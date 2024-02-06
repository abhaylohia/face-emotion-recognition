from unittest import TestCase
import os
import pathlib as pl

from clayrs.content_analyzer.embeddings.embedding_learner.doc2vec import GensimDoc2Vec
from clayrs.content_analyzer.information_processor.nltk import NLTK
from clayrs.content_analyzer.raw_information_source import JSONFile
from test import dir_test_files

file_path = os.path.join(dir_test_files, 'movies_info_reduced.json')


class TestGensimDoc2Vec(TestCase):
    def test_fit(self):
        model_path = "./model_test_Doc2Vec"
        learner = GensimDoc2Vec(model_path, True)
        learner.fit(source=JSONFile(file_path), field_list=["Plot", "Genre"], preprocessor_list=[NLTK()])
        model_path += ".kv"

        self.assertEqual(learner.get_embedding("ace").any(), True)
        self.assertEqual(pl.Path(model_path).resolve().is_file(), True)