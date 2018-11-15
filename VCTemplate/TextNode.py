
import Node

class TextNode (Node.Node):
    def __init__(self, text):
        super().__init__()
        self.text = text
        self.s_text = str(text)

    def __repr__(self):
        return repr(self.s_text)

    def render(self, context):
        context.append(self.s_text)
        return None

