import os
from unittest import TestCase
import pandas as pd

from clayrs.content_analyzer import Ratings
from clayrs.recsys import LinearPredictor, SkLinearRegression, TrainingItemsMethodology
from clayrs.recsys.content_based_algorithm.classifier.classifiers import SkSVC
from clayrs.recsys.recsys import GraphBasedRS, ContentBasedRS
from clayrs.recsys.content_based_algorithm.classifier.classifier_recommender import ClassifierRecommender
from clayrs.recsys.content_based_algorithm.exceptions import NotPredictionAlg, NotFittedAlg
from clayrs.recsys.graph_based_algorithm.page_rank.nx_page_rank import NXPageRank
from clayrs.recsys.graphs import NXFullGraph

from test import dir_test_files

train_ratings = pd.DataFrame.from_records([
    ("A000", "tt0114576", 5, "54654675"),
    ("A001", "tt0114576", 3, "54654675"),
    ("A001", "tt0112896", 1, "54654675"),
    ("A000", "tt0113041", 1, "54654675"),
    ("A002", "tt0112453", 2, "54654675"),
    ("A002", "tt0113497", 4, "54654675"),
    ("A003", "tt0112453", 1, "54654675"),
    ("A003", "tt0113497", 4, "54654675")],
    columns=["from_id", "to_id", "score", "timestamp"])
train_ratings = Ratings.from_dataframe(train_ratings)

# No locally available items for A000
train_ratings_some_missing = pd.DataFrame.from_records([
    ("A000", "not_existent1", 5, "54654675"),
    ("A001", "tt0114576", 3, "54654675"),
    ("A001", "tt0112896", 1, "54654675"),
    ("A000", "not_existent2", 5, "54654675")],
    columns=["from_id", "to_id", "score", "timestamp"])
train_ratings_some_missing = Ratings.from_dataframe(train_ratings_some_missing)

test_ratings = pd.DataFrame.from_records([
    ("A000", "tt0114388", None),
    ("A000", "tt0112302", None),
    ("A001", "tt0113189", None),
    ("A001", "tt0113228", None),
    ("A002", "tt0114319", None),
    ("A002", "tt0114709", None),
    ("A003", "tt0114885", None)],
    columns=["from_id", "to_id", "score"])
test_ratings = Ratings.from_dataframe(test_ratings)


# Each of the cbrs algorithm has its own class tests, so we just take
# one cbrs alg as example. The behaviour is the same for all cbrs alg
class TestContentBasedRS(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.movies_multiple = os.path.join(dir_test_files, 'complex_contents', 'movies_codified/')

    def test_fit(self):
        # Test fit with cbrs algorithm
        alg = LinearPredictor({'Plot': ['tfidf', 'embedding']}, SkLinearRegression())
        cbrs = ContentBasedRS(alg, train_ratings, self.movies_multiple)

        cbrs.fit(num_cpus=1)

        # For the following user the algorithm could be fit
        self.assertIsNotNone(cbrs._user_fit_dic.get("A000"))
        self.assertIsNotNone(cbrs._user_fit_dic.get("A001"))
        self.assertIsNotNone(cbrs._user_fit_dic.get("A002"))
        self.assertIsNotNone(cbrs._user_fit_dic.get("A003"))

        # Test fit with the cbrs algorithm
        # For user A000 no items available locally, so the alg will not be fit for it
        cbrs_missing = ContentBasedRS(alg, train_ratings_some_missing, self.movies_multiple)

        cbrs_missing.fit(num_cpus=1)

        # For user A000 the alg could not be fit, but it could for A001
        self.assertIsNone(cbrs_missing._user_fit_dic.get("A000"))
        self.assertIsNotNone(cbrs_missing._user_fit_dic.get("A001"))

    def test_raise_error_without_fit(self):
        alg = LinearPredictor({'Plot': ['tfidf', 'embedding']}, SkLinearRegression())
        cbrs = ContentBasedRS(alg, train_ratings, self.movies_multiple)

        with self.assertRaises(NotFittedAlg):
            cbrs.rank(train_ratings, num_cpus=1)

        with self.assertRaises(NotFittedAlg):
            cbrs.predict(train_ratings, num_cpus=1)

    def test_rank(self):
        # Test fit with the cbrs algorithm
        alg = LinearPredictor({'Plot': ['tfidf', 'embedding']}, SkLinearRegression())
        cbrs = ContentBasedRS(alg, train_ratings, self.movies_multiple)

        # we must fit the algorithm in order to rank
        cbrs.fit(num_cpus=1)

        # Test ranking with the cbrs algorithm on specified items
        result_rank_filtered = cbrs.rank(test_ratings, num_cpus=1)
        self.assertEqual(len(result_rank_filtered), len(test_ratings))

        # Test ranking with the cbrs algorithm on all available unseen items
        result_rank_all = cbrs.rank(test_ratings, methodology=None, num_cpus=1)
        self.assertTrue(len(result_rank_all) != 0)

        # Test top-n ranking with the cbrs algorithm for only some users
        result_rank_numbered = cbrs.rank(test_ratings, n_recs=2, methodology=None, user_id_list=["A000", "A003"],
                                         num_cpus=1)
        self.assertEqual(set(result_rank_numbered.user_id_column), {"A000", "A003"})
        for user in {"A000", "A003"}:
            result_single = result_rank_numbered.get_user_interactions(user)
            self.assertTrue(len(result_single) == 2)

        # Test ranking with alternative methodology
        result_different_meth = cbrs.rank(test_ratings, methodology=TrainingItemsMethodology(), num_cpus=1)
        for user in set(test_ratings.user_id_column):
            result_single = result_different_meth.get_user_interactions(user)
            result_single_items = set([result_interaction.item_id for result_interaction in result_single])
            items_already_seen_user = set([train_interaction.item_id
                                           for train_interaction in train_ratings.get_user_interactions(user)])
            items_expected_rank = set([train_interaction.item_id
                                       for train_interaction in train_ratings
                                       if train_interaction.item_id not in items_already_seen_user])

            self.assertEqual(items_expected_rank, result_single_items)

        # Test algorithm not fitted
        cbrs = ContentBasedRS(alg, train_ratings_some_missing, self.movies_multiple)

        cbrs.fit(num_cpus=1)
        result_empty = cbrs.rank(test_ratings, user_id_list=['A000'], num_cpus=1)
        self.assertTrue(len(result_empty) == 0)

    def test_predict(self):
        # Test fit with the cbrs algorithm
        alg = LinearPredictor({'Plot': ['tfidf', 'embedding']}, SkLinearRegression())
        cbrs = ContentBasedRS(alg, train_ratings, self.movies_multiple)

        # we must fit the algorithm in order to predict
        cbrs.fit(num_cpus=1)

        # Test predict with the cbrs algorithm on specified items
        result_predict_filtered = cbrs.predict(test_ratings, num_cpus=1)
        self.assertEqual(len(result_predict_filtered), len(test_ratings))

        # Test predict with the cbrs algorithm on all available unseen items
        result_predict_all = cbrs.predict(test_ratings, methodology=None, num_cpus=1)
        self.assertTrue(len(result_predict_all) != 0)

        # Test predict with the cbrs algorithm for only some users
        result_predict_subset = cbrs.predict(test_ratings, methodology=None, user_id_list=["A000", "A003"], num_cpus=1)
        self.assertEqual(set(result_predict_subset.user_id_column), {"A000", "A003"})
        for user in {"A000", "A003"}:
            result_single = result_predict_subset.get_user_interactions(user)
            self.assertTrue(len(result_single) != 0)

        # Test predict with alternative methodology
        result_different_meth = cbrs.predict(test_ratings, methodology=TrainingItemsMethodology(), num_cpus=1)
        for user in set(test_ratings.user_id_column):
            result_single = result_different_meth.get_user_interactions(user)
            result_single_items = set([result_interaction.item_id for result_interaction in result_single])
            items_already_seen_user = set([train_interaction.item_id
                                           for train_interaction in train_ratings.get_user_interactions(user)])
            items_expected_rank = set([train_interaction.item_id
                                       for train_interaction in train_ratings
                                       if train_interaction.item_id not in items_already_seen_user])

            self.assertEqual(items_expected_rank, result_single_items)

        # Test algorithm not fitted
        cbrs = ContentBasedRS(alg, train_ratings_some_missing, self.movies_multiple)

        cbrs.fit(num_cpus=1)
        result_empty = cbrs.predict(test_ratings, user_id_list=['A000'], num_cpus=1)
        self.assertTrue(len(result_empty) == 0)

    def test_predict_raise_error(self):
        alg = ClassifierRecommender({'Plot': ['tfidf', 'embedding']}, SkSVC())
        cbrs = ContentBasedRS(alg, train_ratings, self.movies_multiple)

        # You must fit first in order to predict
        cbrs.fit(num_cpus=1)

        # This will raise error since page rank is not a prediction algorithm
        with self.assertRaises(NotPredictionAlg):
            cbrs.predict(test_ratings)

    def test_fit_rank(self):
        alg = LinearPredictor({'Plot': ['tfidf', 'embedding']}, SkLinearRegression())
        cbrs = ContentBasedRS(alg, train_ratings, self.movies_multiple)

        result = cbrs.fit_rank(test_ratings, save_fit=True, num_cpus=1)

        self.assertTrue(len(result) != 0)

        # with self.assertRaises(NotFittedAlg):
        #     cbrs.rank(test_ratings)


    def test_fit_predict(self):
        alg = LinearPredictor({'Plot': ['tfidf', 'embedding']}, SkLinearRegression())
        cbrs = ContentBasedRS(alg, train_ratings, self.movies_multiple)

        result = cbrs.fit_predict(test_ratings, num_cpus=1)

        self.assertTrue(len(result) != 0)


class TestGraphBasedRS(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # different test ratings from the cbrs since a graph based algorithm
        # can give predictions only to items that are in the graph
        test_ratings = pd.DataFrame.from_records([
            ("A000", "tt0112896", None),
            ("A000", "tt0112453", None),
            ("A001", "tt0114576", None),
            ("A001", "tt0113497", None),
            ("A002", "tt0114576", None),
            ("A002", "tt0113041", None),
            ("A003", "tt0114576", None)],
            columns=["from_id", "to_id", "score"])
        cls.test_ratings = Ratings.from_dataframe(test_ratings)

        train_ratings = pd.DataFrame.from_records([
            ("A000", "tt0114576", 5, "54654675"),
            ("A001", "tt0114576", 3, "54654675"),
            ("A001", "tt0112896", 1, "54654675"),
            ("A000", "tt0113041", 1, "54654675"),
            ("A002", "tt0112453", 2, "54654675"),
            ("A002", "tt0113497", 4, "54654675"),
            ("A003", "tt0112453", 1, "54654675"),
            ("A003", "tt0113497", 4, "54654675")],
            columns=["from_id", "to_id", "score", "timestamp"])
        train_ratings = Ratings.from_dataframe(train_ratings)

        cls.graph = NXFullGraph(train_ratings)

    def test_rank(self):
        # Test rank with the graph based algorithm
        alg = NXPageRank()
        gbrs = GraphBasedRS(alg, self.graph)

        # Test ranking with the graph based algorithm on specified items
        result_rank_filtered = gbrs.rank(self.test_ratings, num_cpus=1)
        self.assertEqual(len(result_rank_filtered), len(self.test_ratings))

        # Test ranking with the gbrs algorithm on all unseen items that are in the graph
        result_rank_all = gbrs.rank(self.test_ratings, methodology=None, num_cpus=1)
        self.assertTrue(len(result_rank_all) != 0)

        # Test top-n ranking with the gbrs algorithm only for some users
        result_rank_numbered = gbrs.rank(self.test_ratings, n_recs=2, methodology=None, user_id_list=["A000", "A003"],
                                         num_cpus=1)
        self.assertEqual(set(result_rank_numbered.user_id_column), {"A000", "A003"})
        for user in {"A000", "A003"}:
            result_single = result_rank_numbered.get_user_interactions(user)
            self.assertTrue(len(result_single) == 2)

        # Test ranking with alternative methodology
        result_different_meth = gbrs.rank(self.test_ratings, methodology=TrainingItemsMethodology(), num_cpus=1)
        for user in set(self.test_ratings.user_id_column):
            result_single = set([pred_rank.item_id for pred_rank in result_different_meth if pred_rank.user_id == user])
            items_already_seen_user = set([original_interaction.item_id
                                           for original_interaction in train_ratings.get_user_interactions(user)])
            items_expected_rank = set([train_interaction.item_id
                                       for train_interaction in train_ratings
                                       if train_interaction.item_id not in items_already_seen_user])

            self.assertEqual(items_expected_rank, result_single)

    def test_predict_raise_error(self):
        alg = NXPageRank()
        gbrs = GraphBasedRS(alg, self.graph)

        # This will raise error since page rank is not a prediction algorithm
        with self.assertRaises(NotPredictionAlg):
            gbrs.predict(self.test_ratings, num_cpus=1)

    def test_rank_filterlist_empty_A000(self):
        # no items to recommend is in the graph for user A000
        test_ratings = pd.DataFrame.from_records([
            ("A000", "not_in_graph", None),
            ("A000", "not_in_graph1", None),
            ("A001", "tt0114576", None),
            ("A001", "tt0113497", None),
            ("A002", "tt0114576", None),
            ("A002", "tt0113041", None),
            ("A003", "tt0114576", None)],
            columns=["from_id", "to_id", "score"])
        test_ratings = Ratings.from_dataframe(test_ratings)

        # Test rank with the graph based algorithm
        alg = NXPageRank()
        gbrs = GraphBasedRS(alg, self.graph)

        # Test ranking with the graph based algorithm with items not present in the graph for A000
        result_rank = gbrs.rank(test_ratings, num_cpus=1)
        self.assertTrue(len(result_rank) != 0)

        # no rank is present for A000
        with self.assertRaises(KeyError):
            result_rank.get_user_interactions('A000')

    def test_rank_filterlist_empty_all(self):
        # different test ratings from the cbrs since a graph based algorithm
        # can give predictions only to items that are in the graph
        test_ratings = pd.DataFrame.from_records([
            ("A000", "not_in_graph", None),
            ("A000", "not_in_graph1", None),
            ("A001", "not_in_graph2", None),
            ("A001", "not_in_graph3", None),
            ("A002", "not_in_graph4", None),
            ("A002", "not_in_graph5", None),
            ("A003", "not_in_graph6", None)],
            columns=["from_id", "to_id", "score"])
        test_ratings = Ratings.from_dataframe(test_ratings)

        # Test rank with the graph based algorithm
        alg = NXPageRank()
        gbrs = GraphBasedRS(alg, self.graph)

        # Test ranking with the graph based algorithm on items not in the graph, we expect it to be empty
        result_rank_empty = gbrs.rank(test_ratings, num_cpus=1)
        self.assertTrue(len(result_rank_empty) == 0)
