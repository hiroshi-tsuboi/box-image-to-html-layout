import sys
import json
import copy
from PIL import Image

#

class Box():
    def __init__(self, mini, maxi, index, color):
        self.mini_ = copy.copy(mini)
        self.maxi_ = copy.copy(maxi)
        self.area_ = (self.maxi_[0] - self.mini_[0] + 1) * (self.maxi_[1] - self.mini_[1] + 1)
        self.index_ = index
        self.parent_ = None
        self.childs_ = []
        self.margin_ = [sys.maxsize, sys.maxsize] # left, top
        self.color_ = copy.copy(color)
    def __eq__(self, other):
        return self.index_ == other.index_
    def size(self):
        return (self.maxi_[0] - self.mini_[0] + 1, self.maxi_[1] - self.mini_[1] + 1)
    def inside(self, pos):
        for i in range(2):
            if pos[i] < self.mini_[i] or self.maxi_[i] < pos[i]:
                return False
        return True
    def include(self, box):
        return self.inside(box.mini_) or self.inside(box.maxi_)
    def dump(self):
        parentIndex = -1
        if self.parent_ is not None:
            parentIndex = self.parent_.index_

        print("index=%d mini=(%d,%d) maxi=(%d,%d) parent=%d margin=%s" % (self.index_, self.mini_[0], self.mini_[1], self.maxi_[0], self.maxi_[1], parentIndex, str(self.margin_)))
        if 0 < len(self.childs_):
            indices = []
            for child in self.childs_:
                indices.append(child.index_)
            print("\tchild(s) = %s" % str(indices))
    def margin(self):
        r = ""
        for i in range(2):
            if self.margin_[i] <= 0 or self.margin_[i] == sys.maxsize:
                continue
            if 0 == i:
                r += "margin-left: %dpx; " % self.margin_[i]
            else:
                r += "margin-top: %dpx; " % self.margin_[i]
        return r

class Group:
    def __init__(self):
        self.boxes_ = []
    def add(self, mini, maxi, index, color):
        self.boxes_.append(Box(mini, maxi, index, color))
    def inside(self, pos):
        for box in self.boxes_:
            if box.inside(pos):
                return True
        return False
    def dump(self):
        for box in self.boxes_:
            box.dump()
    def empty(self):
        return len(self.boxes_) <= 0
    def finalize(self):
        for i in range(2):
            for target in self.boxes_:
                if target.parent_ is not None:
                    margin = target.mini_[i] - target.parent_.mini_[i]
                    if margin < target.margin_[i]:
                        target.margin_[i] = margin
                for box in self.boxes_:
                    if box.maxi_[i] < target.mini_[i]:
                        margin = target.mini_[i] - box.maxi_[i] + 1
                        if margin < target.margin_[i]:
                            target.margin_[i] = margin
                for child in target.childs_:
                    for box in target.childs_:
                        if box.maxi_[i] < child.mini_[i]:
                            margin = child.mini_[i] - box.maxi_[i] + 1
                            if margin < child.margin_[i]:
                                child.margin_[i] = margin

def colorString(color):
    r = "#"
    for i in range(3):
        r += "%02X" % color[i]
    return r

#
# main program
#

# load image

if len(sys.argv) < 2:
    sys.exit()

debug = False
if "--debug" in sys.argv:
    debug = True

filename = sys.argv[1]

image = None

try:
    image = Image.open(filename)
except:
    print("failed to open %s" % filename)
    sys.exit()

if image == None:
    sys.exit()

# create box from image

groups = {}
index = 0

for y in range(image.size[1]):
    for x in range(image.size[0]):
        pos = (x, y)

        pixel = image.getpixel(pos)

        # ignore alpha
        color = (pixel[0], pixel[1], pixel[2])

        if color in groups:
            if groups[color].inside(pos):
                continue
        else:
            groups[color] = Group()

        # extent

        mini = pos
        maxi = [x, y]

        for i in range(2):
            t = [x, y]
            for j in range(pos[i] + 1, image.size[i]):
                t[i] = j
                pixel = image.getpixel((t[0], t[1]))
                if color != (pixel[0], pixel[1], pixel[2]):
                    break
                maxi[i] = j

        # discard thin box
        if (maxi[0] - mini[0]) <= 1 or (maxi[1] - mini[1]) <= 1:
            continue

        groups[color].add(mini, maxi, index, color)
        index += 1

# create box-tree

for group in groups.values():
    for box in group.boxes_:
        miniParent = None
        miniArea = sys.maxsize
        for y in groups.values():
            for x in y.boxes_:
                if box == x:
                    continue
                if x.include(box) and x.area_ < miniArea:
                    miniArea = x.area_
                    miniParent = x
        if miniParent is not None:
            box.parent_ = miniParent
            miniParent.childs_.append(box)

# compute margin left and top
for group in groups.values():
    group.finalize()

# find root
root = None
for group in groups.values():
    for box in group.boxes_:
        if box.parent_ is None:
            if root is not None:
                print("fatal error : base of virtual window must be one.")
                sys.exit()
            root = box

# render html
if not debug:
    print("<!DOCTYPE html>")
    print("<html>")
    print("<head>")
    print('<style type="text/css">')

    stack = [root]
    while 0 < len(stack):
        target = stack.pop()
        if target.parent_ is None:
            option = "flex-flow: column; width: %dpx;" % root.size()[0] 
            print(".box%d { display: flex; background-color: %s; %s}" % (target.index_, colorString(target.color_), option))
        else:
            size = target.size()
            option = child.margin()
            if 0 < len(target.childs_):
                option += "display: flex; "
            print(".box%d { width: %dpx; height: %dpx; color: #404040; background-color: %s; %s}" % (target.index_, size[0], size[1], colorString(target.color_), option))

        for child in target.childs_:
            stack.append(child)

    print("</style>")
    print("</head>")
    print("<body>")

    stack = [root]
    while 0 < len(stack):
        target = stack.pop()
        if type(target) is str:
            print(target)
            continue
        print('<div class="box%d">' % target.index_)
        if 0 == len(target.childs_):
            print("<article>")
            print("<h1>box%d</h1>" % target.index_)
            print("</article>")
        stack.append("</div>")
        for child in reversed(target.childs_):
            stack.append(child)

    print("</body>")
    print("</html>")
    sys.exit()

# debug print
for color, group in groups.items():
    if not group.empty():
        print("color=%s" % str(color))
        group.dump()


