# -*- coding: utf-8 -*-
"""Local Outlier Factor (LOF). Implemented on scikit-learn library.
"""
# Author: Yue Zhao <yuezhao@cs.toronto.edu>
# License: BSD 2 clause

from __future__ import division
from __future__ import print_function

from sklearn.neighbors import LocalOutlierFactor
from sklearn.utils.validation import check_is_fitted
from sklearn.utils.validation import check_array

from .base import BaseDetector


class LOF(BaseDetector):
    """Wrapper of scikit-learn LOF Class with more functionalities.
    Unsupervised Outlier Detection using Local Outlier Factor (LOF).

    The anomaly score of each sample is called Local Outlier Factor.
    It measures the local deviation of density of a given sample with
    respect to its neighbors.
    It is local in that the anomaly score depends on how isolated the object
    is with respect to the surrounding neighborhood.
    More precisely, locality is given by k-nearest neighbors, whose distance
    is used to estimate the local density.
    By comparing the local density of a sample to the local densities of
    its neighbors, one can identify samples that have a substantially lower
    density than their neighbors. These are considered outliers.
    See :cite:`breunig2000lof` for details.

    :param n_neighbors: Number of neighbors to use by default for
        k neighbors.
        If n_neighbors is larger than the number of samples provided,
        all samples will be used.
    :type n_neighbors: int, optional (default=20)

    :param algorithm: Algorithm used to compute the nearest neighbors:

        - 'ball_tree' will use BallTree
        - 'kd_tree' will use KDTree
        - 'brute' will use a brute-force search.
        - 'auto' will attempt to decide the most appropriate algorithm
          based on the values passed to :meth:`fit` method.

        Note: fitting on sparse input will override the setting of
        this parameter, using brute force.

    :type algorithm: {'auto', 'ball_tree', 'kd_tree', 'brute'}, optional

    :param leaf_size: Leaf size passed to BallTree or KDTree. This can
        affect the speed of the construction and query, as well as the memory
        required to store the tree. The optimal value depends on the
        nature of the problem.
    :type leaf_size: int, optional (default=30)

    :param metric: metric used for the distance computation. Any metric from
        scikit-learn or scipy.spatial.distance can be used.

        If 'precomputed', the training input X is expected to be a distance
        matrix.

        If metric is a callable function, it is called on each
        pair of instances (rows) and the resulting value recorded. The callable
        should take two arrays as input and return one value indicating the
        distance between them. This works for Scipy's metrics, but is less
        efficient than passing the metric name as a string.

        Valid values for metric are:

        - from scikit-learn: ['cityblock', 'cosine', 'euclidean', 'l1',
          'l2','manhattan']
        - from scipy.spatial.distance: ['braycurtis', 'canberra',
          'chebyshev', 'correlation', 'dice', 'hamming', 'jaccard',
          'kulsinski', 'mahalanobis', 'matching', 'minkowski',
          'rogerstanimoto', 'russellrao', 'seuclidean', 'sokalmichener',
          'sokalsneath', 'sqeuclidean', 'yule']

        See the documentation for scipy.spatial.distance for details on these
        metrics:
        http://docs.scipy.org/doc/scipy/reference/spatial.distance.html
    :type metric: str or callable, default 'minkowski'

    :param p: Parameter for the Minkowski metric for sklearn.metrics.pairwise.
        pairwise_distances.
        When p = 1, this is equivalent to using manhattan_distance (l1), and
        euclidean_distance (l2) for p = 2. For arbitrary p, minkowski_distance
        (l_p) is used.
        See http://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.pairwise_distances.html
    :type p: int, optional (default=2)

    :param metric_params: Additional keyword arguments for the metric function.
    :type metric_params: dict, optional (default=None)

    :param contamination: The amount of contamination of the data set, i.e.
        the proportion of outliers in the data set. When fitting this is used
        to define the threshold on the decision function.
    :type contamination: float in (0., 0.5), optional (default=0.1)

    :param n_jobs: The number of parallel jobs to run for neighbors search.
        If ``-1``, then the number of jobs is set to the number of CPU cores.
        Affects only kneighbors and kneighbors_graph methods.
    :type n_jobs: int, optional (default=1)

    :var negative_outlier_factor\_:
        The opposite LOF of the training samples. The lower, the more abnormal.
        Inliers tend to have a LOF score close to 1, while outliers tend
        to have a larger LOF score.

        The local outlier factor (LOF) of a sample captures its
        supposed 'degree of abnormality'.
        It is the average of the ratio of the local reachability density of
        a sample and those of its k-nearest neighbors.
    :vartype negative_outlier_factor\_: numpy array, shape (n_samples,)

    :var n_neighbors\_: The actual number of neighbors used for
        kneighbors queries.
    :vartype n_neighbors\_: int
    """

    def __init__(self, n_neighbors=20, algorithm='auto', leaf_size=30,
                 metric='minkowski', p=2, metric_params=None,
                 contamination=0.1, n_jobs=1):
        super(LOF, self).__init__(contamination=contamination)
        self.n_neighbors = n_neighbors
        self.algorithm = algorithm
        self.leaf_size = leaf_size
        self.metric = metric
        self.p = p
        self.metric_params = metric_params
        self.contamination = contamination
        self.n_jobs = n_jobs

    # noinspection PyIncorrectDocstring
    def fit(self, X, y=None):
        """Fit the model using X as training data.

        :param X: Training data. If array or matrix,
            shape [n_samples, n_features],
            or [n_samples, n_samples] if metric='precomputed'.
        :type X: {array-like, sparse matrix, BallTree, KDTree}

        :return: self
        :rtype: object
        """
        # Validate inputs X and y (optional)
        X = check_array(X)
        self._set_n_classes(y)

        self.detector_ = LocalOutlierFactor(n_neighbors=self.n_neighbors,
                                            algorithm=self.algorithm,
                                            leaf_size=self.leaf_size,
                                            metric=self.metric,
                                            p=self.p,
                                            metric_params=self.metric_params,
                                            contamination=self.contamination,
                                            n_jobs=self.n_jobs)
        self.detector_.fit(X=X, y=y)
        self.decision_scores_ = self.detector_.negative_outlier_factor_ * -1
        self._process_decision_scores()
        return self

    def decision_function(self, X):
        X = check_array(X, accept_sparse='csr')
        check_is_fitted(self, ['decision_scores_', 'threshold_', 'labels_'])

        # invert decision_scores_. Outliers comes with higher outlier scores
        # noinspection PyProtectedMember
        return self.detector_._decision_function(X) * -1

    @property
    def negative_outlier_factor_(self):
        """
        The opposite LOF of the training samples. The lower, the more abnormal.
        Inliers tend to have a LOF score close to 1, while outliers tend
        to have a larger LOF score.

        The local outlier factor (LOF) of a sample captures its
        supposed 'degree of abnormality'.
        It is the average of the ratio of the local reachability density of
        a sample and those of its k-nearest neighbors.

        Decorator for scikit-learn LOF attributes.
        """
        return self.detector_.negative_outlier_factor_

    @property
    def n_neighbors_(self):
        """The actual number of neighbors used for kneighbors queries.
        Decorator for scikit-learn LOF attributes.
        """
        return self.detector_.n_neighbors_
