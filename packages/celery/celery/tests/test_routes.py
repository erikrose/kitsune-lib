import unittest2 as unittest


from celery import conf
from celery import routes
from celery.utils import maybe_promise
from celery.utils.functional import wraps
from celery.exceptions import QueueNotFound


def E(queues):
    def expand(answer):
        return routes.Router([], queues).expand_destination(answer)
    return expand


def with_queues(**queues):

    def patch_fun(fun):
        @wraps(fun)
        def __inner(*args, **kwargs):
            prev_queues = conf.QUEUES
            conf.QUEUES = queues
            try:
                return fun(*args, **kwargs)
            finally:
                conf.QUEUES = prev_queues
        return __inner
    return patch_fun


a_queue = {"exchange": "fooexchange",
           "exchange_type": "fanout",
               "binding_key": "xuzzy"}
b_queue = {"exchange": "barexchange",
           "exchange_type": "topic",
           "binding_key": "b.b.#"}


class test_MapRoute(unittest.TestCase):

    @with_queues(foo=a_queue, bar=b_queue)
    def test_route_for_task_expanded_route(self):
        expand = E(conf.QUEUES)
        route = routes.MapRoute({"celery.ping": {"queue": "foo"}})
        self.assertDictContainsSubset(a_queue,
                             expand(route.route_for_task("celery.ping")))
        self.assertIsNone(route.route_for_task("celery.awesome"))

    @with_queues(foo=a_queue, bar=b_queue)
    def test_route_for_task(self):
        expand = E(conf.QUEUES)
        route = routes.MapRoute({"celery.ping": b_queue})
        self.assertDictContainsSubset(b_queue,
                             expand(route.route_for_task("celery.ping")))
        self.assertIsNone(route.route_for_task("celery.awesome"))

    def test_expand_route_not_found(self):
        expand = E(conf.QUEUES)
        route = routes.MapRoute({"a": {"queue": "x"}})
        self.assertRaises(QueueNotFound, expand, route.route_for_task("a"))


class test_lookup_route(unittest.TestCase):

    def test_init_queues(self):
        router = routes.Router(queues=None)
        self.assertDictEqual(router.queues, {})

    @with_queues(foo=a_queue, bar=b_queue)
    def test_lookup_takes_first(self):
        R = routes.prepare(({"celery.ping": {"queue": "bar"}},
                            {"celery.ping": {"queue": "foo"}}))
        router = routes.Router(R, conf.QUEUES)
        self.assertDictContainsSubset(b_queue,
                router.route({}, "celery.ping",
                    args=[1, 2], kwargs={}))

    @with_queues()
    def test_expands_queue_in_options(self):
        R = routes.prepare(())
        router = routes.Router(R, conf.QUEUES, create_missing=True)
        # apply_async forwards all arguments, even exchange=None etc,
        # so need to make sure it's merged correctly.
        route = router.route({"queue": "testq",
                              "exchange": None,
                              "routing_key": None,
                              "immediate": False},
                             "celery.ping",
                             args=[1, 2], kwargs={})
        self.assertDictContainsSubset({"exchange": "testq",
                                       "routing_key": "testq",
                                       "immediate": False},
                                       route)
        self.assertNotIn("queue", route)

    @with_queues(foo=a_queue, bar=b_queue)
    def test_lookup_paths_traversed(self):
        R = routes.prepare(({"celery.xaza": {"queue": "bar"}},
                            {"celery.ping": {"queue": "foo"}}))
        router = routes.Router(R, conf.QUEUES)
        self.assertDictContainsSubset(a_queue,
                router.route({}, "celery.ping",
                    args=[1, 2], kwargs={}))
        self.assertEqual(router.route({}, "celery.poza"), {})


class test_prepare(unittest.TestCase):

    def test_prepare(self):
        from celery.datastructures import LocalCache
        o = object()
        R = [{"foo": "bar"},
                  "celery.datastructures.LocalCache",
                  o]
        p = routes.prepare(R)
        self.assertIsInstance(p[0], routes.MapRoute)
        self.assertIsInstance(maybe_promise(p[1]), LocalCache)
        self.assertIs(p[2], o)

        self.assertEqual(routes.prepare(o), [o])

    def test_prepare_item_is_dict(self):
        R = {"foo": "bar"}
        p = routes.prepare(R)
        self.assertIsInstance(p[0], routes.MapRoute)
