from __future__ import annotations
import abc
from abc import ABC
from typing import Set, Union, Optional, Generator, Dict, TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from clayrs.content_analyzer import Ratings

from clayrs.utils.context_managers import get_progbar


class Methodology(ABC):
    """
    Class which, given a *train set* and a *test set*, has the task to calculate which items must be used in
    order to generate a recommendation list

    The methodologies here implemented follow the 'Precision-Oriented Evaluation of Recommender Systems: An Algorithmic
    Comparison' paper
    """

    def __init__(self, only_greater_eq: float = None):
        self._threshold = only_greater_eq

    def _filter_only_greater_eq(self, split_set: Ratings):
        items_list_greater_eq = [interaction.item_id for interaction in split_set if
                                 interaction.score >= self._threshold]

        return items_list_greater_eq

    def filter_all(self, train_set: Ratings, test_set: Ratings,
                   result_as_iter_dict: bool = False) -> Union[pd.DataFrame, Dict[str, Generator]]:
        """
        Concrete method which calculates for all users of the *test set* which items must be used in order to
        generate a recommendation list

        It takes in input a *train set* and a *test set* and returns a single DataFrame or a generator of a python
        dictionary containing, for every user, all items which must be recommended based on the methodology chosen.

        Args:
            train_set: `Ratings` object which contains the train set of every user
            test_set: `Ratings` object which contains the test set of every user
            result_as_iter_dict (bool): If True the output of the method will be a generator of a dictionary that,
                once evaluated, will contains users as a key and list of item that must be predicted as a value.

                    EXAMPLE:
                        `{'u1': ['i1', 'i2', 'i3'], 'u2': ['i1', 'i4'], ...}`
        Returns:
            A DataFrame or a generator of a python dictionary which contains all items which must be recommended to
            every user based on the methodology chosen.
        """
        user_list = set(test_set.user_id_column)

        with get_progbar(user_list) as pbar:
            pbar.set_description(f"Filtering items based on {str(self)}")

            filtered = {user_id: self.filter_single(user_id, train_set, test_set)
                        for user_id in pbar}

        if not result_as_iter_dict:
            generator_expression = ((user_id, item_to_predict)
                                    for user_id, all_items_to_pred in zip(filtered.keys(), filtered.values())
                                    for item_to_predict in set(all_items_to_pred))

            filtered = pd.DataFrame(generator_expression,
                                    columns=['user_id', 'item_id'])

        return filtered

    @abc.abstractmethod
    def filter_single(self, user_id: str, train_set: Ratings, test_set: Ratings) -> Generator:
        """
        Abstract method in which must be specified how to calculate which items must be part of the recommendation list
        of a single user
        """
        raise NotImplementedError

    @abc.abstractmethod
    def __str__(self):
        raise NotImplementedError


class TestRatingsMethodology(Methodology):
    """
    Class which, given a *train set* and a *test set*, has the task to calculate which items must be used in
    order to generate a recommendation list

    With TestRatingsMethodology, given a user $u$, items to recommend for $u$ are simply those items that appear in its
    *test set*

    If the `only_greater_eq` parameter is set, then only items with rating score $>=$ only_greater_eq will be
    returned

    Args:
        only_greater_eq: float which acts as a filter, if specified only items with
            rating score $>=$ only_greater_eq will be returned
    """

    def __init__(self, only_greater_eq: float = None):
        super(TestRatingsMethodology, self).__init__(only_greater_eq)

    def __str__(self):
        return "TestRatingsMethodology"

    def __repr__(self):
        return f"TestRatingsMethodology(only_greater_eq={self._threshold})"

    def filter_single(self, user_id: str, train_set: Ratings, test_set: Ratings) -> Generator:
        """
        Method that returns items that need to be part of the recommendation list of a single user.
        Since it's the TestRatings Methodology, only items that appear in the *test set* of the user will be returned.

        Args:
            user_id: User of which we want to calculate items that must appear in its recommendation list
            train_set: `Ratings` object which contains the train set of every user
            test_set: `Ratings` object which contains the test set of every user
        """
        user_test = test_set.get_user_interactions(user_id)

        if self._threshold is not None:
            filtered_items = (interaction.item_id
                              for interaction in user_test if interaction.score >= self._threshold)
        else:
            # TestRatings just returns the test set of the user
            filtered_items = (interaction.item_id for interaction in user_test)

        return filtered_items


class TestItemsMethodology(Methodology):
    """
    Class which, given a *train set* and a *test set*, has the task to calculate which items must be used in
    order to generate a recommendation list

    With TestItemsMethodology, given a user $u$, items to recommend for $u$ are all items that appear in the
    *test set* of every user excluding those items that appear in the *train set* of $u$

    If the `only_greater_eq` parameter is set, then only items with rating score $>=$ only_greater_eq will be
    returned

    Args:
        only_greater_eq: float which acts as a filter, if specified only items with
            rating score $>=$ only_greater_eq will be returned
    """

    def __init__(self, only_greater_eq: float = None):
        super(TestItemsMethodology, self).__init__(only_greater_eq)

        self._filtered_test_set_items: Optional[Set] = None

    def __str__(self):
        return "TestItemsMethodology"

    def __repr__(self):
        return f"TestItemsMethodology(only_greater_eq={self._threshold})"

    def filter_single(self, user_id: str, train_set: Ratings, test_set: Ratings) -> Generator:
        """
        Method that returns items that need to be part of the recommendation list of a single user.
        Since it's the TestItems Methodology, all items that appear in the *test set* of every user will be returned,
        except for those that appear in the *train set* of the user passed as parameter

        Args:
            user_id: User of which we want to calculate items that must appear in its recommendation list
            train_set: `Ratings` object which contains the train set of every user
            test_set: `Ratings` object which contains the test set of every user
        """
        already_seen_items_it = (interaction.item_id for interaction in train_set.get_user_interactions(user_id))

        filtered_test_set_items = test_set.item_id_column
        if self._threshold is not None:
            if self._filtered_test_set_items is None:
                self._filtered_test_set_items = set(self._filter_only_greater_eq(test_set))

            filtered_test_set_items = self._filtered_test_set_items

        filtered_items = yield from set(filtered_test_set_items) - set(already_seen_items_it)

        return filtered_items


class TrainingItemsMethodology(Methodology):
    """
    Class which, given a *train set* and a *test set*, has the task to calculate which items must be used in
    order to generate a recommendation list

    With TrainingItemsMethodology, given a user $u$, items to recommend for $u$ are all items that appear in the
    'train set' of every user excluding those items that appear in the 'train set' of $u$

    If the `only_greater_eq` parameter is set, then only items with rating score $>=$ only_greater_eq will be
    returned

    Args:
        only_greater_eq: float which acts as a filter, if specified only items with
            rating score $>=$ only_greater_eq will be returned
    """

    def __init__(self, only_greater_eq: float = None):
        super(TrainingItemsMethodology, self).__init__(only_greater_eq)

        self._filtered_train_set_items: Optional[Set] = None

    def __str__(self):
        return "TrainingItemsMethodology"

    def __repr__(self):
        return f"TrainingItemsMethodology(only_greater_eq={self._threshold})"

    def filter_single(self, user_id: str, train_set: Ratings, test_set: Ratings) -> Generator:
        """
        Method that returns items that needs to be part of the recommendation list of a single user.
        Since it's the TrainingItems Methodology, all items that appear in the *train set* of every user will be
        returned, except for those that appear in the *train set* of the user passed as parameter

        Args:
            user_id: User of which we want to calculate items that must appear in its recommendation list
            train_set: `Ratings` object which contains the train set of every user
            test_set: `Ratings` object which contains the test set of every user
        """
        already_seen_items_it = (interaction.item_id for interaction in train_set.get_user_interactions(user_id))

        filtered_train_set_items = train_set.item_id_column
        if self._threshold is not None:
            if self._filtered_train_set_items is None:
                self._filtered_train_set_items = set(self._filter_only_greater_eq(train_set))

            filtered_train_set_items = self._filtered_train_set_items

        filtered_items = yield from set(filtered_train_set_items) - set(already_seen_items_it)

        return filtered_items


class AllItemsMethodology(Methodology):
    """
    Class which, given a *train set* and a *test set*, has the task to calculate which items must be used in
    order to generate a recommendation list

    With AllItemsMethodology, given a user $u$, items to recommend for $u$ are all items that appear in 'items_list'
    parameter excluding those items that appear in the *train set* of $u$

    Args:
        items_list: Items set that must appear in the recommendation list of every user
    """

    def __init__(self, items_list: Set[str]):
        self._items_list = items_list
        super(AllItemsMethodology, self).__init__(None)

    def __str__(self):
        return "AllItemsMethodology"

    def __repr__(self):
        return f"AllItemsMethodology(items_list={self._items_list})"

    def filter_single(self, user_id: str, train_set: Ratings, test_set: Ratings) -> Generator:
        """
        Method that returns items that needs to be part of the recommendation list of a single user.
        Since it's the AllItems Methodology, all items that appear in the `items_list` parameter of the constructor
        will be returned, except for those that appear in the *train set* of the user passed as parameter

        Args:
            user_id: User of which we want to calculate items that must appear in its recommendation list
            train_set: `Ratings` object which contains the train set of every user
            test_set: `Ratings` object which contains the test set of every user
        """
        already_seen_items_it = (interaction.item_id for interaction in train_set.get_user_interactions(user_id))

        filtered_items = yield from set(self._items_list) - set(already_seen_items_it)

        return filtered_items
