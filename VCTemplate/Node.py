

class Node (object):
    @classmethod
    def renderSequence(cls, context, sequence):
        for node in sequence:
            r = node.render(context)
            if r is not None:
                return r
        return r

    def __init__(self, context):
        self.parse_context = context

