import unittest
from unittest import TestCase
import pandas as pd

from clayrs.content_analyzer.ratings_manager.ratings import Ratings
from clayrs.recsys.partitioning import HoldOutPartitioning, KFoldPartitioning, BootstrapPartitioning

original_ratings = pd.DataFrame.from_dict(
    {'from_id': ["001", "001", "002", "002", "002", "003", "003", "004", "004"],
     'to_id': ["aaa", "bbb", "aaa", "ddd", "ccc", "ccc", "aaa", "ddd", "ccc"],
     'rating': [0.8, 0.7, -0.4, 1.0, 0.4, 0.1, -0.3, 0.5, 0.7]})

original_ratings = Ratings.from_dataframe(original_ratings)


class TestPartitioning(TestCase):
    def check_partition_correct(self, train, test, original):
        original_list = list(original)
        train_list = list(train)
        test_list = list(test)

        # Check that train and test are a partition
        train_not_in_test = [row for row in train_list if row not in test_list]
        self.assertCountEqual(train_list, train_not_in_test)  # Count so regardless of order
        test_not_in_train = [row for row in test_list if row not in train_list]
        self.assertCountEqual(test_list, test_not_in_train)  # Count so regardless of order

        # Check that the union of the two give the original data
        union_list = train_list + test_list
        self.assertCountEqual(original_list, union_list)  # Count so regardless of order


class TestKFoldPartitioning(TestPartitioning):

    def test_split_all(self):

        kf = KFoldPartitioning(n_splits=2)

        result_train, result_test = kf.split_all(original_ratings)

        for train, test in zip(result_train, result_test):
            self.check_partition_correct(train, test, original_ratings)

        result_train, result_test = kf.split_all(original_ratings, user_id_list={'001'})

        for train, test in zip(result_train, result_test):
            only_001_train = set(train.user_id_column)
            only_001_test = list(test.user_id_column)

            self.assertTrue(len(only_001_train) == 1)
            self.assertTrue(len(only_001_test) == 1)

            self.assertIn("001", only_001_train)
            self.assertIn("001", only_001_test)

            original_001 = original_ratings.filter_ratings(user_list=['001'])

            self.check_partition_correct(train, test, original_001)

    def test_split_some_missing(self):
        kf = KFoldPartitioning(n_splits=3)

        result_train, result_test = kf.split_all(original_ratings)

        for train, test in zip(result_train, result_test):
            # It's the only user for which is possible to perform 3 split
            only_002_train = set(train.user_id_column)
            only_002_test = set(test.user_id_column)

            self.assertTrue(len(only_002_train) == 1)
            self.assertTrue(len(only_002_test) == 1)

            self.assertIn("002", only_002_train)
            self.assertIn("002", only_002_test)

            original_002 = original_ratings.filter_ratings(user_list=['002'])

            self.check_partition_correct(train, test, original_002)

    def test_split_all_raise_error(self):
        kf = KFoldPartitioning(n_splits=3, skip_user_error=False)

        with self.assertRaises(ValueError):
            kf.split_all(original_ratings)


class TestHoldOutPartitioning(TestPartitioning):

    def test_split_all(self):
        hold_percentage = 0.3

        ho = HoldOutPartitioning(train_set_size=hold_percentage)

        result_train, result_test = ho.split_all(original_ratings)

        for train, test in zip(result_train, result_test):
            self.check_partition_correct(train, test, original_ratings)

            train_percentage = (len(train) / len(original_ratings))
            self.assertEqual(hold_percentage, train_percentage)

        result_train, result_test = ho.split_all(original_ratings, user_id_list={'001'})

        for train, test in zip(result_train, result_test):
            only_001_train = set(train.user_id_column)
            only_001_test = set(test.user_id_column)

            self.assertTrue(len(only_001_train) == 1)
            self.assertTrue(len(only_001_test) == 1)

            self.assertIn("001", only_001_train)
            self.assertIn("001", only_001_test)

            original_001 = original_ratings.filter_ratings(user_list=['001'])

            self.check_partition_correct(train, test, original_001)

    def test_split_some_missing(self):

        hold_percentage = 0.4

        ho = HoldOutPartitioning(train_set_size=hold_percentage)

        result_train, result_test = ho.split_all(original_ratings)

        for train, test in zip(result_train, result_test):
            # It's the only user for which is possible to hold 0.4 as train
            only_002_train = set(train.user_id_column)
            only_002_test = set(test.user_id_column)

            self.assertTrue(len(only_002_train) == 1)
            self.assertTrue(len(only_002_test) == 1)

            self.assertIn("002", only_002_train)
            self.assertIn("002", only_002_test)

            original_002 = original_ratings.filter_ratings(user_list=['002'])

            self.check_partition_correct(train, test, original_002)

    def test_split_all_raise_error(self):
        hold_percentage = 0.4

        ho = HoldOutPartitioning(train_set_size=hold_percentage, skip_user_error=False)

        with self.assertRaises(ValueError):
            ho.split_all(original_ratings)

    def test__check_percentage(self):

        # Bigger than 1
        hold_percentage = 1.5
        with self.assertRaises(ValueError):
            HoldOutPartitioning(train_set_size=hold_percentage)

        # Negative percentage
        hold_percentage = -0.2
        with self.assertRaises(ValueError):
            HoldOutPartitioning(train_set_size=hold_percentage)


class TestBootstrapPartitioning(TestPartitioning):

    def check_partition_correct(self, train, test, original):
        original_list = list(original)
        train_list = list(train)
        test_list = list(test)

        # Check that train and test are a partition
        train_not_in_test = [row for row in train_list if row not in test_list]
        self.assertCountEqual(train_list, train_not_in_test)  # Count so regardless of order
        test_not_in_train = [row for row in test_list if row not in train_list]
        self.assertCountEqual(test_list, test_not_in_train)  # Count so regardless of order

        # Check that the union of the two give the original data.
        # We remove any duplicate that can naturally happen due to the resampling of the
        # bootstrap method
        union_list = list(set(train_list)) + test_list
        self.assertCountEqual(original_list, union_list)  # Count so regardless of order

    def test_split_all(self):

        bs = BootstrapPartitioning(random_state=5)

        [train], [test] = bs.split_all(original_ratings)

        # 001, 003 and 004 had not enough ratings and so with this particular random state
        # the resampling will give us empty test set for those user, meaning that they will not be
        # present in the final train and test set
        self.assertTrue("001" not in train.user_id_column)
        self.assertTrue("002" in train.user_id_column)
        self.assertTrue("003" not in train.user_id_column)
        self.assertTrue("004" not in train.user_id_column)

        # only user 002 is present in train and test set
        original_002 = original_ratings.filter_ratings(['002'])
        self.check_partition_correct(train, test, original_002)

    def test_split_raise_error(self):
        bs = BootstrapPartitioning(random_state=5)

        # with this particular random state user 001 has not enough ratings and the resampling
        # will get all its ratings, making the test set empty, and so an error will be raised
        # by the split_single method
        user_001_rat = original_ratings.get_user_interactions('001')

        with self.assertRaises(ValueError):
            bs.split_single(user_001_rat)


if __name__ == '__main__':
    unittest.main()
