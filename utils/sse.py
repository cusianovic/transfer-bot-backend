import queue
from .user import userList

class MessageAnnouncer:
    def __init__(self):
        self.listeners = {}

    def listen(self, id):
        q = queue.Queue(maxsize=5)
        self.listeners[id] = q
        return q
    
    def globalAnnounce(self, msg):
        for id in list(reversed(self.listeners.keys())):
            try:
                self.listeners[id].put_nowait(msg)
            except:
                del self.listeners[id]
                if id in userList: del userList[id]

    def announce(self, id, msg):
        try:
            self.listeners[id].put_nowait(msg)
        except:
            del self.listeners[id]


def format_sse(data: str, event=None) -> str:
    data = data.replace("\n", "%0A")
    msg = f'data: {data}\n\n'
    if event is not None:
        msg = f'event: {event}\n{msg}'
    return msg



