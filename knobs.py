'''
what's a good name for this? knob?


from knob import Limiter
for x in Limiter( range(10), calls=5, per=60 ):
    do_something(x)

'''

'''
a knob service takes some creds and an knob name, and allows a user to modify the calls and per values
http://knob.franxman.com/knobs/myknob/?calls=1&per=0.0&clid=12345 -> {'calls':50, 'per':10, 'clients':3}
   if the knob doesnt exist, it creates and saves the values,
   otherwise, it returns the values from storage
the clients have to send some sort of id, so that the server can keep track of how many simultaneous instances of the knob there are.
This allows the client to scale the rate accordingly.

if the user doesnt name their knob, then what?   host + filepath + line number ?
Should the site organize the knobs by host? or just filepath + line_number
Should collect any stats?  call count? sparklines?

from knobs import knob
knob.set_default_service('http://knobs.franxman.com/knobs/', creds={'username':me, 'password':pw } )
for item in knob( range(10), name='myloop' )
    item.do_something()

But there could also be single use knobs that get used by many processes.
with knob(name='myknob'):
    do_something()
Could this sleep on exit if the tasks returns too quickly?


'''


from time import time, sleep


class Knob(object):
    ''' Knob - a tunable rate limiter what can be used as a smart sleep call, a generator, or a context manager.
    '''
    SERVICE = None
    CREDS = None

    def __init__(self, items=[], name='', calls=1, per=0.0, recheck=60, service=None, creds=None):
        self.iterable = items
        self.name = name
        self.max_calls = calls
        self.per = per
        self.recheck = recheck

        self.call_count = 0

        now = time()
        self.next_allowed = now + per
        self.next_check = now + recheck

        # allow local service cfg, otherwise we'll rely on the settings shared
        # by the class
        if service:
            self.SERVICE = service
        if creds:
            self.CREDS = creds


    def __repr__(self):
        if self.name:
            name = self.name + ' '
        else:
            name = ''
        return "{n}limited to {c} calls per {p} seconds".format(n=name, c=self.max_calls, p=self.per)


    # for use as a sleep call
    def __call__(self):
        self.call_count += 1

        if self.call_count > self.max_calls:
            now = time()
            if now < self.next_allowed:
                # sleep til window closes
                print "rate limiter {n} sleeping...\n\n".format(n=self.name)
                sleep(self.next_allowed - now)

            self.next_allowed = time() + self.per
            self.call_count = 1

        self.update_rate()


    # as a generator
    def __iter__(self, *args, **kwargs):
        for item in self.iterable:
            self()
            yield item


    # for use as a Context Manager
    def __enter__(self):
        pass


    def __exit__(self, type, value, tb):
        self()


    def update_rate(self):
        now = time()
        if now > self.next_check:
            # here we would hit redis and see if max_calls and/or per have
            # changed
            print "updating rates from {s}".format(s=self.SERVICE)
            self.next_check = now + self.recheck


    @classmethod
    def set_default_service(cls, service, creds):
        cls.SERVICE = service
        cls.CREDS = creds



def test():
    limit = Knob(name='myloop', calls=3, per=5)
    print limit

    for x in range(10):
        limit()
        print x, "." * 20
        sleep(1)



def test_gen():
    l = Knob(items=range(100), name='mygenloop')
    print l
    for item in l:
        print item, "." * 20

    l = Knob(range(5), per=3)
    print l
    for item in l:
        print item, "," * 20

    l = Knob(range(7), name='mygenloop', calls=3, per=5)
    print l
    for item in l:
        print item, "_" * 20



def test_service_cfg():
    Knob.set_default_service('class default', '')
    limiter = Knob(recheck=1)
    limiter()
    sleep(2)
    limiter()

    limiter = Knob(recheck=1, service='local service', creds='x')
    limiter()
    sleep(2)
    limiter()

    limiter = Knob(recheck=1)  # should revert to class defaults
    limiter()
    sleep(2)
    limiter()



def test_as_context_manager():
    with Knob(calls=1, per=5) as rl:
        print "doing something"
        sleep(1)

    rl = Knob(calls=2, per=5)
    with rl:
        print "doing more"
        sleep(1)

    with rl:
        print"doing even more"

    with rl:
        print "we get the point"

    print "2 per 5"
    for x in range(10):
        with rl:
            print "x", x
