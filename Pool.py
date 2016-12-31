# -*- coding: utf-8 -*-
__author__ = 'xscn2426'

import Queue

class Pool(type):
	pool = dict()
	statistic = 0
	def __new__(metacls, *a, **k):
		def __del__(self):
			Q = Pool.pool.get(self.__class__)
			if Q is None:
				Q = Queue.Queue()
			self.return_to_pool()
			Q.put(self)
			print "######### Pool Size #############", Q.qsize()
			Pool.pool[self.__class__] = Q
		a[-1]['__del__'] = __del__
		return type.__new__(metacls, *a, **k)

	def __call__(clas, *a, **k):
		if Pool.pool.get(clas) and not Pool.pool.get(clas).empty():
			r = Pool.pool[clas].get()
			r.__init__(*a, **k)
			return r
		else:
			Pool.statistic += 1
			print('Pool.pool is empty, allocate one all %d' % Pool.statistic)
			return type.__call__(clas, *a, **k)
