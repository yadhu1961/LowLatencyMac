#!/usr/bin/env python
# encoding: utf-8

"""

pydispatcher demo

requirements: pip install pydispatcher

"""

from pydispatch import dispatcher

ORDER_CREATED_SIGNAL = 'order.created'
ORDER_STATUS_CHANGED_SIGNAL = 'order.status_changed'


class Order(object):
    def __init__(self, number):
        self.number = number
        self.status = 'PENDING'

    def __repr__(self):
        return "{} [{}]".format(
            self.number,
            self.status
        )

    def __str__(self):
        return "{} [{}]".format(
            self.number,
            self.status
        )

    def __unicode__(self):
        return u"{} [{}]".format(
            self.number,
            self.status
        )


class OrderService(object):
    """Order Service"""

    def createOrder(self, number):
        order = Order(number)
        dispatcher.send(
            signal=ORDER_CREATED_SIGNAL, sender=self, order=order
        )
        return order

    def closeOrder(self, order):
        order.status = 'CLOSED'
        dispatcher.send(
            signal=ORDER_STATUS_CHANGED_SIGNAL, sender=self, order=order
        )
        return order

    def __repr__(self):
        return self.__doc__

    def __str__(self):
        return self.__doc__

    def __unicode__(self):
        return self.__doc__


# debug listener, prints sender and params
def debug_listener(sender, **kwargs):
    print "[DEBUG] '{}' sent data '{}'".format(
        sender,
        ", ".join([
            "{} => {}".format(key, value) for key, value in kwargs.items()
        ])
    )


# send email listener
def send_order_email_listener(sender, order):
    print "[MAIL] sending email about order {}".format(
        sender, order
    )


# send email every time when order is created
dispatcher.connect(
    send_order_email_listener,
    signal=ORDER_CREATED_SIGNAL,
    sender=dispatcher.Any
)

# debug all signals
dispatcher.connect(
    debug_listener,
    signal=ORDER_CREATED_SIGNAL,
    sender=dispatcher.Any
)

dispatcher.connect(
    debug_listener,
    signal=ORDER_STATUS_CHANGED_SIGNAL,
    sender=dispatcher.Any
)


# let's go
s = OrderService()
o1 = s.createOrder('1234/Z/12')
o2 = s.createOrder('1234/A/12')
s.closeOrder(o2)
s.closeOrder(o1)