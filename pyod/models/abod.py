# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function

from itertools import combinations

import numpy as np
from sklearn.neighbors import KDTree
from sklearn.neighbors import NearestNeighbors
from sklearn.utils import check_array
from sklearn.utils.validation import check_is_fitted
from .base import BaseDetector
from ..utils.utility import check_parameter


def _calculate_wocs(curr_pt, X, X_ind):
    """
    Calculated the variance of weighted cosine of a point
    wcos = (<a_curr, b_curr>/((|a_curr|*|b_curr|)^2)

    :param curr_pt: the sample to be calculated
    :type curr_pt: array, shape (1, n_features)
    :param X: the training dataset
    :type X: numpy array of shape (n_samples, n_features)
    :param X_ind: the valid index of the training data
    :type X_ind: list
    :return: the variance of cosine angle
    :rtype: float
    """
    wcos_list = []
    curr_pair_inds = list(combinations(X_ind, 2))
    for j, (a_ind, b_ind) in enumerate(curr_pair_inds):
        a = X[a_ind, :]
        b = X[b_ind, :]

        # TODO: implement a faster solution
        # curr_pt_mat = np.tile(curr_pt, (n, 1)) # broadcast
        # Broadcast and do mat comparison to find the index

        # skip if no angle can be formed
        if np.array_equal(a, curr_pt) or np.array_equal(b, curr_pt):
            continue

        a_curr = a - curr_pt
        b_curr = b - curr_pt

        # wcos = (<a_curr, b_curr>/((|a_curr|*|b_curr|)^2)
        wcos = np.dot(a_curr, b_curr) / (
                np.linalg.norm(a_curr, 2) ** 2) / (
                       np.linalg.norm(b_curr, 2) ** 2)
        wcos_list.append(wcos)

    return np.var(wcos_list)


# noinspection PyPep8Naming
class ABOD(BaseDetector):
    """
    ABOD class for Angle-base Outlier Detection.
    For an observation, the variance of its weighted cosine scores to all
    neighbors could be viewed as the outlying score.
    See :cite:`kriegel2008angle` for details.

    Two version of ABOD are supported:
    Fast ABOD: use k nearest neighbors to approximate for complexity reduction
    Original ABOD: consider all training points with high time complexity at
    O(n^3).

    :param contamination: the amount of contamination of the data set, i.e.
        the proportion of outliers in the data set. Used when fitting to
        define the threshold on the decision function.
    :type contamination: float in (0, 0.5], optional (default=0.1)

    :param n_neighbors: Number of neighbors to use by default
        for k neighbors queries.
    :type n_neighbors: int, optional (default=10)

    :param method: {'fast', 'default'}

        - 'fast': fast ABOD. Only consider n_neighbors of training points
        - 'default': original ABOD with all training points, slow
    :type method: str
    """

    def __init__(self, contamination=0.1, n_neighbors=5, method='fast'):
        super(ABOD, self).__init__(contamination=contamination)
        self.method = method
        self.n_neighbors = n_neighbors

    def fit(self, X, y=None):

        # Validate inputs X and y (optional)
        X = check_array(X)
        self._set_n_classes(y)

        self.X_train_ = X
        self.n_train_ = X.shape[0]
        self.decision_scores_ = np.zeros([self.n_train_, 1])

        if self.method == 'fast':
            self._fit_fast()
        elif self.method == 'default':
            self._fit_default()
        else:
            raise ValueError(self.method, "is not a valid method")

        # flip the scores
        self.decision_scores_ = self.decision_scores_.ravel() * -1
        self._process_decision_scores()
        return self

    def _fit_default(self):
        """
        Default ABOD method. Use all training points with high complexity
        O(n^3). For internal use only
        :return: None
        """
        for i in range(self.n_train_):
            curr_pt = self.X_train_[i, :]

            # get the index pairs of the neighbors, remove itself from index
            X_ind = list(range(0, self.n_train_))
            X_ind.remove(i)

            self.decision_scores_[i, 0] = _calculate_wocs(curr_pt,
                                                          self.X_train_,
                                                          X_ind)
        return self

    def _fit_fast(self):
        """
        Fast ABOD method. Only use n_neighbors for angle calculation
        Internal use only
        :return: None
        """

        # make sure the n_neighbors is in the range
        check_parameter(self.n_neighbors, 1, self.n_train_)

        self.tree_ = KDTree(self.X_train_)

        neigh = NearestNeighbors(n_neighbors=self.n_neighbors)
        neigh.fit(self.X_train_)
        ind_arr = neigh.kneighbors(n_neighbors=self.n_neighbors,
                                   return_distance=False)

        for i in range(self.n_train_):
            curr_pt = self.X_train_[i, :]
            X_ind = ind_arr[i, :]
            self.decision_scores_[i, 0] = _calculate_wocs(curr_pt,
                                                          self.X_train_,
                                                          X_ind)
        return self

    # noinspection PyPep8Naming
    def decision_function(self, X):

        check_is_fitted(self,
                        ['X_train_', 'n_train_', 'decision_scores_',
                         'threshold_',
                         'labels_'])
        X = check_array(X)

        if self.method == 'fast':  # fast ABOD
            # outliers have higher outlier scores
            return self._decision_function_fast(X) * -1
        else:  # default ABOD
            return self._decision_function_default(X) * -1

    def _decision_function_default(self, X):
        """
        Internal method for predicting outlier scores using default ABOD

        :param X: The training input samples. Sparse matrices are accepted only
            if they are supported by the base estimator.
        :type X: numpy array of shape (n_samples, n_features)
        :return: The anomaly score of the input samples.
        :rtype: array, shape (n_samples,)
        """
        # initialize the output score
        pred_score = np.zeros([X.shape[0], 1])

        for i in range(X.shape[0]):
            curr_pt = X[i, :]
            # get the index pairs of the neighbors
            X_ind = list(range(0, self.n_train_))
            pred_score[i, :] = _calculate_wocs(curr_pt, self.X_train_, X_ind)

        return pred_score.ravel()

    def _decision_function_fast(self, X):
        """
        Internal method for predicting outlier scores using Fast ABOD

        :param X: The training input samples. Sparse matrices are accepted only
            if they are supported by the base estimator.
        :type X: numpy array of shape (n_samples, n_features)
        :return: The anomaly score of the input samples.
        :rtype: array, shape (n_samples,)
        """

        check_is_fitted(self, ['tree_'])
        # initialize the output score
        pred_score = np.zeros([X.shape[0], 1])

        # get the indexes of the X's k nearest training points
        _, ind_arr = self.tree_.query(X, k=self.n_neighbors)

        for i in range(X.shape[0]):
            curr_pt = X[i, :]
            X_ind = ind_arr[i, :]
            pred_score[i, :] = _calculate_wocs(curr_pt, self.X_train_, X_ind)

        return pred_score.ravel()
