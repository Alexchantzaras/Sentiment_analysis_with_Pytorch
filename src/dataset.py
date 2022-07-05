from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset, DataLoader
from vectorizer import *
from nltk.corpus import stopwords

import nltk
import pandas as pd
import re

class TextDataset(Dataset):
    def __init__(self, text_data, vectorizer, language='english'):
        """
        Args:
            text_data (pandas.DataFrame): the dataset
            vectorizer (TextVectorizer): vectorizer instantiated from dataset
            language (str): the language in which the stopwords belong to
        """

        self._vectorizer = vectorizer
        self._train_data, self._test_data = train_test_split(text_data, test_size=0.2)
        self._train_data, self._val_data = train_test_split(self.train_data, test_size=0.25)

        nltk.download('stopwords')
        self._stopwords = set(stopwords.words(language))

        self._lookup_dict = {
            'train': (self.train_data, len(self.train_data)),
            'val': (self.val_data, len(self.val_data)),
            'test': (self.test_data, len(self.test_data))
        }

        self.set_split('train')

    @property
    def train_data(self):
        return self._train_data

    @property
    def test_data(self):
        return self._test_data

    @property
    def val_data(self):
        return self._val_data

    def generate_batches(self, batch_size, shuffle=True, drop_last=True, device="cpu"):

        """
        Args:
            batch_size: the batch_size that the dataloader produces (defined in the arguments given in the main.ipynb)
            shuffle: parameter to randomize the selection of data in batches
            drop_last: The drop_last=True parameter ignores the last batch (when the number of examples in our dataset is not divisible
            by our batch_size)
            device: the device that the batches will be loaded for processing
        """

        dataloader = DataLoader (
            dataset=self, 
            batch_size=batch_size, 
            shuffle=shuffle, 
            drop_last=drop_last
        )

        for data_dict in dataloader:
            out_data_dict = {}
            for name, _ in data_dict.items():
                out_data_dict[name] = data_dict[name].to(device)
            yield out_data_dict


    @classmethod
    def load_dataset_and_make_vectorizer(cls, text_csv, vectorizer_mode="onehot"):
        """ Load dataset and make a new vectorizer from scratch

        Args:
            text_csv (str): location of the dataset

        Returns:
            an instance of textDataset
        """

        text_data = pd.read_csv(text_csv)
        seq_len = text_data.text.str.len().max()
        if seq_len > 1000:
            seq_len = 359
        return cls(text_data, TextVectorizer.from_dataframe(text_data, mode=vectorizer_mode, seq_len=seq_len))

    @property
    def vectorizer(self):
        """ Returns the vectorizer """

        return self._vectorizer

    def set_split(self, split="train"):
        """ Selects the splits in the dataset using a column in the dataframe

        Args:
            split (str): one of "train", "val", or "test"
        """

        self._target_split = split
        self._target_data, self._target_size = self._lookup_dict[split]

    def __string_processing(self, string):
        """ Preprocess text

        Args:
            string (str): a single data point

        Returns:
            str: the processed string
        """

        string = string.lower()
        # Remove all non-word characters (everything except numbers and letters)
        string = re.sub(r"[^\w\s]", '', string)
        # Remove stopwords and lemmatize each one
        string = ' '.join([w for w in string.split() if not w in self._stopwords])

        return string

    def __len__(self):
        return self._target_size

    def __getitem__(self, index):
        """ The primary entry point method for PyTorch datasets

        Args:
            index (int): the index to the data point
            
        Returns:
            a dict of the data point's features (x_data) and label (y_target)
        """
        
        row = self._target_data.iloc[index]
        row_text = self.__string_processing(row.text)
        text_vector = self._vectorizer.vectorize(row_text)
        label_index = self._vectorizer.label_vocab.lookup_token(row.label)

        return {'x_data': text_vector, 'y_target': label_index}