#-- coding: utf-8 -*-
__author__ = 'xscn2426'

import time

# 无限次数计时器
FOREVER = -1

# 计时器状态
CANCELLED 	= 1
READY 		= 2

# 时间单位
HOUR 	= 1
MINUTE 	= 2
SECONDS = 3
FRAME 	= 4

# debug 时间流逝速度, 正常1.0
TIME_ELAPSED = 0.001

def get_seconds(hour, minute, seconds, frame):
	return hour * 3600.0 + minute * 60.0 + seconds + frame / 30.0

def to_seconds(src, src_unit):
	if src_unit == SECONDS:
		return src
	elif src_unit == MINUTE:
		return src * 60.0
	elif src_unit == HOUR:
		return src * 3600.0
	elif src_unit == FRAME:
		return src / 30.0

def seconds_to(src, dst_unit):
	if dst_unit == SECONDS:
		return src
	elif dst_unit == MINUTE:
		return src / 60.0
	elif dst_unit == HOUR:
		return src / 3600.0
	elif dst_unit == FRAME:
		return src * 30.0

def to_time(src, src_unit, dst_unit):
	seconds = to_seconds(src, src_unit)
	return seconds_to(seconds, dst_unit)

class Timer(object):

	def __init__(self, create_time, rounds, callback, interval_rounds=0, interval_offset=0, times=1, remainder = 0, rremainder = 0):
		self.create_time = create_time
		self.rounds	= rounds
		self.callback = callback
		self.status	= READY
		self.times = times
		self.remainder = remainder

		self.rescheduleRounds = interval_rounds
		self.rescheduleOffset = interval_offset
		self.rescheduleRemainder = rremainder

	def cancelled(self):
		return self.status == CANCELLED

	def decrement(self):
		self.rounds -= 1

	def get_offset(self):
		return self.rescheduleOffset

	def ready(self):
		return self.rounds == 0 and self.remainder <= 0

	def reset(self):
		self.status = READY
		self.rounds = self.rescheduleRounds
		self.remainder = self.rescheduleRemainder

	def cancel(self):
		self.status = CANCELLED

	def can_reuse(self):
		return self.times >= 1 or self.times == FOREVER

	def can_lower(self):
		return self.remainder > 0 and self.rounds == 0

	def deal(self):
		try:
			self.callback()
		except Exception as e:
			print e
		finally:
			if self.times != FOREVER:
				self.times -= 1

class TimerSlot(object):

	def __init__(self):
		super(TimerSlot, self).__init__()
		self.timers = []		# timers

	def add_delay_timer(self, create_time, rounds, callback, remainder = 0):
		timer = Timer(create_time, rounds, callback, remainder = remainder)
		self.timers.append(timer)
		return timer

	def add_repeat_timer(self, create_time, rounds, callback, interval_rounds, interval_offset, times, remainder = 0, rremainder = 0):
		timer = Timer(create_time, rounds, callback, interval_rounds, interval_offset, times, remainder=remainder, rremainder = rremainder)
		self.timers.append(timer)
		return timer

	def add_timer(self, timer):
		self.timers.append(timer)

	def process(self):
		to_remove = []
		to_reschedule = []
		for timer in self.timers:
			if timer.cancelled():
				to_remove.append(timer)
			elif timer.ready():
				timer.deal()
				to_remove.append(timer)
				if timer.can_reuse():
					to_reschedule.append(timer)
			else:
				timer.decrement()
		for t in to_remove:
			self.timers.remove(t)
		return to_reschedule

	def hprocess(self):
		to_remove = []
		to_reschedule = []
		to_lower = []
		for timer in self.timers:
			if timer.cancelled():
				to_remove.append(timer)
			elif timer.ready():
				timer.deal()
				to_remove.append(timer)
				if timer.can_reuse():
					to_reschedule.append(timer)
			elif timer.can_lower():
				to_lower.append(timer)
				to_remove.append(timer)
			else:
				timer.decrement()
		for t in to_remove:
			self.timers.remove(t)
		return to_reschedule, to_lower

	def clear(self):
		for timer in self.timers:
			timer.cancel()

class TimerWheel(object):

	def __init__(self, wheelSize, resolution, time_unit):
		super(TimerWheel, self).__init__()
		self.time_unit = time_unit
		self.wheelSize = wheelSize
		self.resolution = resolution
		self.wheels = []
		for i in xrange(wheelSize):
			self.wheels.append(TimerSlot())

		self.cursor = 0

		self.pre = None
		self.next = None

	def delay_exec(self, delay, callback):
		offset = int(delay / self.resolution)
		rounds = int(offset / self.wheelSize)
		self.wheels[self.idx(self.cursor + offset)].add_delay_timer(time.time(), rounds, callback)

	def repeat_exec(self, delay, interval, times, callback):
		offset = int(delay / self.resolution)
		rounds = int(offset / self.wheelSize)
		interval_offset = int(interval / self.resolution)
		interval_rounds = int(interval / self.wheelSize)
		self.wheels[self.idx(self.cursor + offset)].add_repeat_timer(time.time(), rounds, callback, interval_rounds, interval_offset, times)

	def repeat_forever_exec(self, delay, interval, callback):
		self.repeat_exec(delay, interval, FOREVER, callback)

	def add_hierarchical_delay_timer(self, offset, rounds, remainder, callback):
		return self.wheels[self.idx(self.cursor + offset)].add_delay_timer(time.time(), rounds, callback, remainder=remainder)

	def add_hierarchical_repeat_timer(self, offset, rounds, remainder, callback, roffset, rrounds, rremainder, times):
		return self.wheels[self.idx(self.cursor + offset)].add_repeat_timer(time.time(), rounds, callback, rrounds, roffset, times, rremainder = rremainder, remainder=remainder)

	def reschedule(self, timer):
		timer.reset()
		self.wheels[self.idx(self.cursor + timer.get_offset())].add_timer(timer)

	def idx(self, cursor):
		return int(cursor % self.wheelSize)

	def get_now(self):
		return time.time()

	def tick(self):
		while True:
			slot = self.wheels[self.cursor]
			to_reschedule = slot.process()
			for timer in to_reschedule:
				self.reschedule(timer)
			time.sleep(to_seconds(self.resolution, self.time_unit))
			self.cursor = (self.cursor + 1) % self.wheelSize

	def wait(self):
		time.sleep(to_seconds(self.resolution * TIME_ELAPSED, self.time_unit))

	def update_cursor(self, timerWheel):
		old_cursor = self.cursor
		self.cursor = (self.cursor + 1) % self.wheelSize
		if old_cursor + 1 == self.wheelSize and self.pre:
			self.pre.update_cursor(timerWheel)
			self.pre.expire(timerWheel)
		if self == timerWheel.chain.hourWheel:
			print "hour ", self.cursor

	def expire(self, timerWheel):
		slot = self.wheels[self.cursor]
		to_reschedule, to_lower = slot.hprocess()
		for timer in to_reschedule:
			self.hreschedule(timer, timerWheel)
		if to_lower:
			for timer in to_lower:
				timerWheel.lower_timer(timer)
		elif to_lower and not self.next:
			print "----------has to lower why not next!--------------"

	def hreschedule(self, timer, timerWheel):
		timer.reset()
		timerWheel.reschedule(timer)

	def hadd_timer(self, timer, offset=None):
		if offset is None:
			offset = timer.get_offset()
		self.wheels[self.idx(self.cursor + offset)].add_timer(timer)

	def clear(self):
		for slot in self.wheels:
			slot.clear()

class TimerWheelChain(object):
	def __init__(self, timerWheel):
		super(TimerWheelChain, self).__init__()
		self.timerWheel = timerWheel

		self.hourWheel = TimerWheel(24, 1, HOUR)
		self.minuteWheel = TimerWheel(60, 1, MINUTE)
		self.secondsWheel = TimerWheel(60, 1, SECONDS)
		self.frameWheel = TimerWheel(30, 1, FRAME)

		self.head = self.hourWheel
		self.tail = self.frameWheel

		self.hourWheel.next = self.minuteWheel
		self.minuteWheel.pre = self.hourWheel
		self.minuteWheel.next = self.secondsWheel
		self.secondsWheel.pre = self.minuteWheel
		self.secondsWheel.next = self.frameWheel
		self.frameWheel.pre = self.secondsWheel

	def tick(self):
		while True:
			self.tail.expire(self.timerWheel)
			self.tail.wait()
			self.tail.update_cursor(self.timerWheel)

class HierarchicalTimerWheel(object):

	def __init__(self):
		super(HierarchicalTimerWheel, self).__init__()
		self.chain = TimerWheelChain(self)

	def lower_timer(self, timer):
		delay = timer.remainder
		(dhour, hour_remainder), (dminute, minute_remainder), (dseconds, seconds_remainder), (dframes,_) = self.calc_param(delay)
		if dhour:
			rounds = int(dhour / 24)
			if rounds == dhour / 24:
				rounds -= 1
			timer.remainder = hour_remainder
			timer.rounds = rounds
			self.chain.hourWheel.hadd_timer(timer, dhour)
		elif dminute:
			timer.remainder = minute_remainder
			timer.rounds = 0
			self.chain.minuteWheel.hadd_timer(timer, dminute)
		elif dseconds:
			timer.remainder = seconds_remainder
			timer.rounds = 0
			self.chain.secondsWheel.hadd_timer(timer, dseconds)
		elif dframes:
			timer.remainder = 0
			timer.rounds = 0
			self.chain.frameWheel.hadd_timer(timer, dframes)
		else:
			timer.remainder = 0
			timer.rounds = 0
			self.chain.frameWheel.hadd_timer(timer, 1)

	def reschedule(self, timer):
		interval = timer.get_offset()
		(dhour, hour_remainder), (dminute, minute_remainder), (dseconds, seconds_remainder), (dframes,_) = self.calc_param(interval)
		if dhour:
			rounds = int(dhour / 24)
			if rounds == dhour / 24:
				rounds -= 1
			timer.remainder = hour_remainder
			timer.rounds = rounds
			self.chain.hourWheel.hadd_timer(timer, dhour)
		elif dminute:
			timer.remainder = minute_remainder
			timer.rounds = 0
			self.chain.minuteWheel.hadd_timer(timer, dminute)
		elif dseconds:
			timer.remainder = seconds_remainder
			timer.rounds = 0
			self.chain.secondsWheel.hadd_timer(timer, dseconds)
		elif dframes:
			timer.remainder = 0
			timer.rounds = 0
			self.chain.frameWheel.hadd_timer(timer, dframes)
		else:
			timer.remainder = 0
			timer.rounds = 0
			self.chain.frameWheel.hadd_timer(timer, 1)

	def get_time(self):
		hour = self.chain.hourWheel.cursor
		minute = self.chain.minuteWheel.cursor
		seconds = self.chain.secondsWheel.cursor
		frames = self.chain.frameWheel.cursor

		return get_seconds(hour, minute, seconds, frames)

	def calc_param(self, delay):
		now = self.get_time()

		delay_hour = delay + now
		hour = int(to_time(delay_hour, SECONDS, HOUR))
		delay_minutes = delay_hour - hour * 3600.0
		minute = max(0, int(to_time(delay_minutes, SECONDS, MINUTE)))
		delay_seconds = delay_minutes - minute * 60.0
		seconds = max(0, int(to_time(delay_seconds, SECONDS, SECONDS)))
		delay_frames = delay_seconds - seconds
		frames = max(0, int(to_time(delay_frames, SECONDS, FRAME)))

		cur_hour = self.chain.hourWheel.cursor
		cur_minute = self.chain.minuteWheel.cursor
		cur_seconds = self.chain.secondsWheel.cursor
		cur_frames = self.chain.frameWheel.cursor

		dhour = hour - cur_hour, delay_hour - get_seconds(hour, 0, 0, 0)
		dminute = minute - cur_minute, delay_minutes - get_seconds(0, minute, 0, 0)
		dseconds = seconds - cur_seconds, delay_seconds - get_seconds(0, 0, seconds, 0)
		dframes = frames - cur_frames, 0

		return dhour, dminute, dseconds, dframes

	def delay_exec(self, delay, callback):
		(dhour, hour_remainder), (dminute, minute_remainder), (dseconds, seconds_remainder), (dframes,_) = self.calc_param(delay)
		if dhour:
			rounds = int(dhour / 24)
			return self.chain.hourWheel.add_hierarchical_delay_timer(dhour, rounds, hour_remainder, callback)
		elif dminute:
			return self.chain.minuteWheel.add_hierarchical_delay_timer(dminute, 0, minute_remainder, callback)
		elif dseconds:
			return self.chain.secondsWheel.add_hierarchical_delay_timer(dseconds, 0, seconds_remainder, callback)
		elif dframes:
			return self.chain.frameWheel.add_hierarchical_delay_timer(dframes, 0, 0, callback)
		else:
			return self.chain.frameWheel.add_hierarchical_delay_timer(1, 0, 0, callback)

	def repeat_exec(self, delay, interval, times, callback):
		(dhour, hour_remainder), (dminute, minute_remainder), (dseconds, seconds_remainder), (dframes,_) = self.calc_param(delay)
		rounds = 0
		remainder = 0

		if dhour:
			offset = dhour
			rounds = int(dhour / 24)
			remainder = hour_remainder
		elif dminute:
			offset = dminute
			remainder = minute_remainder
		elif dseconds:
			offset = dseconds
			remainder = seconds_remainder
		elif dframes:
			offset = dframes
		else:
			offset = 1

		if dhour:
			return self.chain.hourWheel.add_hierarchical_repeat_timer(offset, rounds, remainder, callback, interval, 0, 0, times)
		elif dminute:
			return self.chain.minuteWheel.add_hierarchical_repeat_timer(offset, rounds, remainder, callback, interval, 0, 0, times)
		elif dseconds:
			return self.chain.secondsWheel.add_hierarchical_repeat_timer(offset, rounds, remainder, callback, interval, 0, 0, times)
		else:
			return self.chain.frameWheel.add_hierarchical_repeat_timer(offset, rounds, remainder, callback, interval, 0, 0, times)

	def repeat_forever_exec(self, delay, interval, callback):
		self.repeat_exec(delay, interval, FOREVER, callback)

	def tick(self):
		self.chain.tick()

	def clear(self):
		self.chain.hourWheel.clear()
		self.chain.minuteWheel.clear()
		self.chain.secondsWheel.clear()
		self.chain.frameWheel.clear()



wheel = HierarchicalTimerWheel()
def cb(delay):
	print "++++++++++++++++++++++++", wheel.get_time(), delay

print "start time", wheel.get_time()
wheel.delay_exec(0.1, lambda: cb(0.1))
wheel.delay_exec(10, lambda: cb(10))
wheel.delay_exec(20, lambda: cb(20))
wheel.delay_exec(30, lambda: cb(30))
wheel.delay_exec(40, lambda: cb(40))
wheel.delay_exec(50, lambda: cb(50))
wheel.delay_exec(60, lambda: cb(60))
wheel.delay_exec(70, lambda: cb(70))
wheel.delay_exec(60, lambda: cb(60))

wheel.delay_exec(100, lambda: cb(100))
wheel.delay_exec(100, lambda: cb(101))
wheel.delay_exec(100, lambda: cb(102))
#
# wheel.repeat_exec(3700, 3700, 20, lambda: cb(25))

# wheel.delay_exec(3600 * 25, lambda: cb(102))

repeat_timer = wheel.repeat_exec(25, 24, 11, lambda: cb("every 2.2s"))

def cancel_cb():
	#repeat_timer.cancel()
	wheel.clear()

wheel.delay_exec(50, lambda :cancel_cb())

def delay_delay():
	wheel.delay_exec(100, lambda: cb(4100))

#wheel.delay_exec(4000, lambda: delay_delay())

wheel.tick()