from datetime import timedelta


class acdTime(object):
    __slots__ = ('data')

    def __init__(self, data):
        self.data = data

    def average(self):
        s = timedelta(seconds=0)
        for t in self.data:
            s += t
        return s / len(self.data)

    def maximum(self):
        return max(self.data)
