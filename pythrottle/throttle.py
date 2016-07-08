from functools import wraps
from threading import Semaphore, Thread
import time
import logging

__author__ = 'erider'


class throttle(object):
    """
    A decorator that throttles the call rate of a callee.

    Examples:

        @throttle(per_second=2)
        def myfunc() # I will be called a maximum of twice a second

        @throttle(per_second=0.1)
        def myfunc() # I will be called a maximum of once every 10 seconds

        def my_rate():
           delta = output_rate - input_rate
           ........
           return ret

        @throttle(rate_function=my_rate)
        def myfunc() # I will dynamically use CPU based on input and output performance.
    """
    _per_second = 3
    _rate_function = None
    _mutex = Semaphore(1)
    _count_mutex = Semaphore(1)
    _time_mutex = Semaphore(1)
    _cih_counter = 0
    _log = None
    _running_count = 0
    _interval_start = time.time()
    _barrier = Semaphore(0)
    _rate_trigger = None
    _throttling = True
    _triggering = True
    _pending_mutex = Semaphore(0)
    _interval_count = 0
    _pending = 0

    def __init__(self, per_second=None, rate_function=None):
        if rate_function:
            self._rate_function = rate_function
        if per_second:
            self._per_second = per_second
        self.__log = logging.getLogger(throttle.__name__)


    def __del__(self):
        # print 'Deleting'
        pass

    def get_throttle_period(self):
        '''
        Calculate the period required to sleep between stimulating barrier entry.
        :return: 1/rate per second
        '''
        if self._rate_function:
            self._per_second = self._rate_function()
            self.__log.debug("Getting per_second from rate function (%s)" % self._per_second)
        return float(1 / float(self._per_second))


    def _get_per_second(self):
        self.get_throttle_period()
        return self._per_second

    def _set_interval_start(self, start):
        '''
        Set when the interval started.
        :param start: A (float) in seconds.
        :return: When the interval started
        '''
        self._mutex.acquire()
        self._interval_start = start
        ret = self._interval_start
        self._mutex.release()
        return ret

    def get_interval_start(self):
        '''
        :return: When the interval started.
        '''
        self._mutex.acquire()
        ret = self._interval_start
        self._mutex.release()
        return ret

    def get_expired_time(self):
        '''
        Get the amount of time expired since the interval started.
        :return: The amount of time expired since the interval started.
        '''
        ret = self.get_interval_start()
        return time.time() - ret

    def _push_count(self):
        '''
        Do all the entry housekeeping for the throttler.
        :return: The current thread count doing the function.
        '''
        self._count_mutex.acquire()
        self._pending = self._pending + 1
        if self._running_count == 0:
            self._interval_count = 0
            self._set_interval_start(time.time())
            self._start_pending_checks()
        self._count_mutex.release()
        self._barrier.acquire()
        self._count_mutex.acquire()
        self._pending = self._pending - 1
        self._running_count = self._running_count + 1
        self._interval_count = self._interval_count + 1
        ret = self._running_count
        self._count_mutex.release()
        return ret

    def get_total_run_count(self):
        '''
        :return: The total number of threads that have existed during the interval.
        '''
        self._count_mutex.acquire()
        ret = self._interval_count
        self._count_mutex.release()
        return ret

    def get_running_count(self):
        '''
        Get the number of threads doing the function
        :return: The number of threads doing the function.
        '''
        self._count_mutex.acquire()
        ret = self._running_count
        self._count_mutex.release()
        return ret

    def _pop_count(self):
        '''
        Do all the exit housekeeping for the throttler

        :return:
        '''
        self._count_mutex.acquire()
        self._running_count = self._running_count - 1
        if self._running_count < 0:
            self._running_count = 0;
        ret = self._running_count
        self._count_mutex.release()
        return ret

    def _throttler(self):
        '''
        Ok when somebody calls this function start this rate throttler
        It basically releases the barrier every interval time to let
        the function enter.  This could be across multiple threads.
        We stop this throttler when the last guy exits a given interval
        We restart it when the first guy enters a given interval (The first guy also starts the interval)
        '''
        while True:
            period = self.get_throttle_period()
            self.__log.debug("Pending(%s)" % (self.get_pending()))
            # These are atomic so don't reuse a variable here.
            if self.get_total_run_count() < self._get_max_allowed() and self.are_pending():
                self.__log.debug("Releasing barrier")
                self._barrier.release()
            time.sleep(period)
            if not self.are_pending():
                break
        self.__log.debug("Rate monitor terminated")

    def are_pending(self):
        self._count_mutex.acquire()
        ret = self._pending > 0
        self._count_mutex.release()
        return ret

    def get_pending(self):
        self._count_mutex.acquire()
        ret = self._pending
        self._count_mutex.release()
        return ret

    def _start_pending_checks(self, value=True):
        '''
        Set Triggering
        :param value: bool
        '''
        self._mutex.acquire()
        if self._rate_trigger:
            if not self._rate_trigger.is_alive():
                self.__log.debug("Restarting rate monitor")
                self._rate_trigger = Thread(target=self._throttler)
                self._rate_trigger.start()
        else:
                self._rate_trigger = Thread(target=self._throttler)
                self._rate_trigger.start()
        self._mutex.release()

    def _get_max_allowed(self):
        '''
        Determine the current maximum count for this throttle period mathmatically/
        :return: The total quantity of calls that could be made during this period.
        '''
        ret = self.get_expired_time()
        return ret * self._get_per_second()

    def __call__(self, fn):
        @wraps(fn)
        def throttled(*args, **kwargs):
            ret = None
            try:
                self._push_count()
                self._log.debug(
                    'Calling Function(%s,%s) Pending(%s)' % (fn.__name__, time.time(), self.get_pending()))
                ret = fn(*args, **kwargs)
            finally:
                self._pop_count()
            return ret

        self._log = logging.getLogger(fn.__name__)
        return throttled
