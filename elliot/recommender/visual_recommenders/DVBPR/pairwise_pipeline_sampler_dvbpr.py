"""
Module description:

"""

__version__ = '0.3.0'
__author__ = 'Vito Walter Anelli, Claudio Pomo, Daniele Malitesta'
__email__ = 'vitowalter.anelli@poliba.it, claudio.pomo@poliba.it, daniele.malitesta@poliba.it'

import tensorflow as tf
import os
from PIL import Image

import numpy as np
import random


class Sampler:
    def __init__(self, indexed_ratings, item_indices, images_path, output_image_size, epochs):
        np.random.seed(42)
        random.seed(42)
        self._indexed_ratings = indexed_ratings
        self._item_indices = item_indices
        self._users = list(self._indexed_ratings.keys())
        self._nusers = len(self._users)
        self._items = list({k for a in self._indexed_ratings.values() for k in a.keys()})
        self._nitems = len(self._items)
        self._ui_dict = {u: list(set(indexed_ratings[u])) for u in indexed_ratings}
        self._lui_dict = {u: len(v) for u, v in self._ui_dict.items()}

        self._images_path = images_path
        self._output_image_size = output_image_size
        self._epochs = epochs

    def read_features_triple(self, user, pos, neg):
        # load positive and negative item images
        im_pos = Image.open(os.path.join(self._images_path, str(pos.numpy())) + '.jpg')
        im_neg = Image.open(os.path.join(self._images_path, str(neg.numpy())) + '.jpg')

        try:
            im_pos.load()
        except ValueError:
            print(f'Image at path {pos}.jpg was not loaded correctly!')

        try:
            im_neg.load()
        except ValueError:
            print(f'Image at path {neg}.jpg was not loaded correctly!')

        if im_pos.mode != 'RGB':
            im_pos = im_pos.convert(mode='RGB')
        if im_neg.mode != 'RGB':
            im_neg = im_neg.convert(mode='RGB')

        im_pos = (np.array(im_pos.resize(self._output_image_size)) - np.float32(127.5)) / np.float32(127.5)
        im_neg = (np.array(im_neg.resize(self._output_image_size)) - np.float32(127.5)) / np.float32(127.5)
        return user.numpy(), pos.numpy(), im_pos, neg.numpy(), im_neg

    def step(self, events: int, batch_size: int):
        r_int = np.random.randint
        n_users = self._nusers
        n_items = self._nitems
        ui_dict = self._ui_dict
        lui_dict = self._lui_dict

        actual_inter = (events // batch_size) * batch_size * self._epochs

        counter_inter = 1

        def sample():
            u = r_int(n_users)
            ui = ui_dict[u]
            lui = lui_dict[u]
            if lui == n_items:
                sample()
            i = ui[r_int(lui)]

            j = r_int(n_items)
            while j in ui:
                j = r_int(n_items)
            return u, i, j

        for ep in range(self._epochs):
            for _ in range(events):
                yield sample()
                if counter_inter == actual_inter:
                    return
                else:
                    counter_inter += 1

    def pipeline(self, num_users, batch_size):
        def load_func(u, p, n):
            b = tf.py_function(
                self.read_features_triple,
                (u, p, n,),
                (np.int64, np.int64, np.float32, np.int64, np.float32)
            )
            return b

        data = tf.data.Dataset.from_generator(generator=self.step,
                                              output_shapes=((), (), ()),
                                              output_types=(tf.int64, tf.int64, tf.int64),
                                              args=(num_users, batch_size))
        data = data.map(load_func, num_parallel_calls=tf.data.experimental.AUTOTUNE)
        data = data.batch(batch_size=batch_size)
        data = data.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)

        return data

    # this is only for evaluation
    def read_image(self, item):
        """
        Args:
            item: Integer

        Returns:
            item id, image
        """
        im = Image.open(os.path.join(self._images_path, str(item)) + '.jpg')

        try:
            im.load()
        except ValueError:
            print(f'Image at path {item}.jpg was not loaded correctly!')

        if im.mode != 'RGB':
            im = im.convert(mode='RGB')

        im = (np.array(im.resize(self._output_image_size)) - np.float32(127.5)) / np.float32(127.5)
        return item, im
