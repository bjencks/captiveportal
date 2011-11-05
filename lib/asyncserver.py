import socket
import select
import errno
import logging
import ipaddr

LOGGER = logging.getLogger('asyncserver')

class CloseException(Exception):
    pass
class BreakException(Exception):
    pass

def while_not_eagain(fun):
    """Repeatedly calls fun until it raises socket.error for EAGAIN, or returns
    true. Other exceptions are passed through.
    
    fun takes no arguments; the caller should define fun to close over any data
    it needs.

    """
    while True:
        try:
            if fun():
                break
        except socket.error as e:
            if e.errno == errno.EAGAIN:
                break
            else:
                raise
        except BreakException:
            break

def addrinfo_to_str(addr, port, family):
    if family == socket.AF_INET:
        return '{0}:{1}'.format(addr, port)
    elif family == socket.AF_INET6:
        return '[{0}]:{1}'.format(addr, port)

class WrappedSocket:
    def __init__(self, sock):
        self.socket = sock
        self.socket.setblocking(0)

    def fileno(self):
        return self.socket.fileno()

class BufferedSocket(WrappedSocket):
    """A generic class for a connection-based protocol where each connection
    contains exactly one request and response, such as non-keepalive HTTP.

    """
    def __init__(self, sock, connlist):
        WrappedSocket.__init__(self, sock)
        self.connlist = connlist
        self.readbuf = b''
        self.writebuf = b''
        self.connlist.add(self, select.EPOLLIN)
        self.addr = self.getpeernameinfo()
        LOGGER.info('Accepted connection from {0}'.format(addrinfo_to_str(*self.addr)))

    def getpeernameinfo(self):
        """Returns (remote, port, family) tuple

        """
        (addr, port) = socket.getnameinfo(self.socket.getpeername(),
                              socket.NI_NUMERICHOST | socket.NI_NUMERICSERV)
        return (addr, port, self.socket.family)

    def get_address(self):
        if (self.addr[2] == socket.AF_INET):
            return ipaddr.IPv4Address(self.addr[0])
        elif (self.addr[2] == socket.AF_INET6):
            return ipaddr.IPv6Address(self.addr[0])
        else:
            raise Exception("Unknown address family: {0:d}".format(self.addr[2]))

    def request_complete(self):
        raise NotImplementedException()

    def generate_response(self):
        raise NotImplementedException()

    def doread(self):
        def helper():
            buf = self.socket.recv(1024)
            if len(buf) == 0:
                # If we read 0 without raising EAGAIN, the connection is closed.
                raise CloseException()
            self.readbuf += buf
        while_not_eagain(helper)
        if self.request_complete():
            self.generate_response()
            LOGGER.debug('[{0}] Request complete: {1!r} Returning response {2!r}'.format(addrinfo_to_str(*self.addr), self.readbuf, self.writebuf))
            self.connlist.modify(self, select.EPOLLOUT)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_CORK, 1)

    def dowrite(self):
        def helper():
            if len(self.writebuf) == 0:
                raise BreakException()
            wrlen = self.socket.send(self.writebuf)
            if wrlen <= 0:
                raise CloseException()
            self.writebuf = self.writebuf[wrlen:]
        while_not_eagain(helper)
        if len(self.writebuf) == 0:
            LOGGER.debug('[{0}] Response sent'.format(addrinfo_to_str(*self.addr)))
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_CORK, 0)
            self.connlist.modify(self, 0)
            self.socket.shutdown(socket.SHUT_RDWR)

    def close(self):
        LOGGER.debug('[{0}] Closing connection'.format(addrinfo_to_str(*self.addr)))
        self.connlist.remove(self)
        self.socket.close()
 
    def handle_event(self, event):
        try:
            if event & select.EPOLLHUP:
                raise CloseException()
            if event & select.EPOLLIN:
                self.doread()
            if event & select.EPOLLOUT:
                self.dowrite()
        except CloseException:
            self.close()
        except:
            LOGGER.exception("Exception occured handling client {0}".format(addrinfo_to_str(*self.addr)))
            self.close()

    def __repr__(self):
        return '<{0} object with remote peer {1}>'.format(
                self.__class__.__name__, addrinfo_to_str(*self.addr))

    def __str__(self):
        return repr(self)


class ListenSocket(WrappedSocket):
    def __init__(self, sock, sockclass, connlist):
        WrappedSocket.__init__(self, sock)
        self.sockclass = sockclass
        self.connlist = connlist
        self.connlist.add(self, select.EPOLLIN)
        self.addr = addrinfo_to_str(*self.getsocknameinfo())
        LOGGER.info('Now listening on {0}'.format(self.addr))

    def getsocknameinfo(self):
        """Returns (remote, port, family) tuple

        """
        (addr, port) = socket.getnameinfo(self.socket.getsockname(),
                              socket.NI_NUMERICHOST | socket.NI_NUMERICSERV)
        return (addr, port, self.socket.family)

    def handle_event(self, event):
        if event & select.EPOLLIN:
            def helper():
                newsock, addr = self.socket.accept()
                self.sockclass(newsock, self.connlist)
            while_not_eagain(helper)

class EPollConnList:
    def __init__(self):
        self.epoll = select.epoll()
        self.conns = dict()

    def add(self, conn, events):
        self.epoll.register(conn.fileno(), events | select.EPOLLET)
        self.conns[conn.fileno()] = conn
    
    def modify(self, conn, events):
        self.epoll.modify(conn.fileno(), events | select.EPOLLET)

    def remove(self, conn):
        self.epoll.unregister(conn.fileno())
        del self.conns[conn.fileno()]

    def mainloop(self):
        while True:
            events = self.epoll.poll()
            for (fd, event) in events:
                #LOGGER.debug('Got event [{0}] on conn {1!r}'.format(event_to_str(event), self.conns[fd]))
                self.conns[fd].handle_event(event)

EVENTS = [(select.EPOLLIN, 'EPOLLIN'),
          (select.EPOLLOUT, 'EPOLLOUT'),
          (select.EPOLLPRI, 'EPOLLPRI'),
          (select.EPOLLERR, 'EPOLLERR'),
          (select.EPOLLHUP, 'EPOLLHUP'),
          (select.EPOLLET, 'EPOLLET'),
          (select.EPOLLONESHOT, 'EPOLLONESHOT'),
          (select.EPOLLRDNORM, 'EPOLLRDNORM'),
          (select.EPOLLRDBAND, 'EPOLLRDBAND'),
          (select.EPOLLWRNORM, 'EPOLLWRNORM'),
          (select.EPOLLWRBAND, 'EPOLLWRBAND'),
          (select.EPOLLMSG, 'EPOLLMSG')]
def event_to_str(ev):
    names = []
    for (val, name) in EVENTS:
        if ev & val:
            names.append(name)
    return ','.join(names)

def register_listeners(port, connlist, sockclass):
    addrinfos = socket.getaddrinfo(None, port, 0, socket.SOCK_STREAM,
                                   socket.SOL_TCP, socket.AI_PASSIVE)
    for (family, socktype, proto, _, sockaddr) in addrinfos:
        sock = socket.socket(family, socktype, proto)
        if family == socket.AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(sockaddr)
        sock.listen(255)
        wrapped = ListenSocket(sock, sockclass, connlist)

def main(port, sockclass):
    connlist = EPollConnList()
    register_listeners(port, connlist, sockclass)
    connlist.mainloop()
