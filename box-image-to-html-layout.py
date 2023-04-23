import sys
import json
import copy
from PIL import Image

#

class Box():
    def __init__(self, mini, maxi, index):
        self.mini_ = copy.copy(mini)
        self.maxi_ = copy.copy(maxi)
        self.area_ = (self.maxi_[0] - self.mini_[0] + 1) * (self.maxi_[1] - self.mini_[1] + 1)
        self.index_ = index
        self.parent_ = -1
        self.childs_ = []
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
        print("index=%d mini=(%d,%d) maxi=(%d,%d) parent=%d" % (self.index_, self.mini_[0], self.mini_[1], self.maxi_[0], self.maxi_[1], self.parent_))
        if 0 < len(self.childs_):
            print("\tchild(s) = %s" % str(self.childs_))

class Group:
    def __init__(self):
        self.boxes_ = []
    def add(self, mini, maxi, index):
        self.boxes_.append(Box(mini, maxi, index))
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
    def find(self, index):
        for box in self.boxes_:
            if box.index_ == index:
                return box
        return None


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

        groups[color].add(mini, maxi, index)
        index += 1

# create box-tree
childs = {}
for group in groups.values():
    for box in group.boxes_:
        childs[box.index_] = box.childs_

for group in groups.values():
    for box in group.boxes_:
        miniIndex = -1
        miniArea = sys.maxsize
        for y in groups.values():
            for x in y.boxes_:
                if box == x:
                    continue
                if x.include(box) and x.area_ < miniArea:
                    miniArea = x.area_
                    miniIndex = x.index_
        if 0 <= miniIndex:
            box.parent_ = miniIndex
            childs[miniIndex].append(box.index_)

# find root
root = None
for group in groups.values():
    for box in group.boxes_:
        if box.parent_ < 0:
            if None != root:
                print("fatal error : base of virtual window must be one.")
                sys.exit()
            root = box

# TODO render html
print("<!DOCTYPE html>")
print("<html>")
print("<head>")
print('<style type="text/css">')

stack = [root]
while 0 < len(stack):
    target = stack.pop()
    baseSize = target.size()
    for index in childs[target.index_]:
        for color, group in groups.items():
            box = group.find(index)
            if box is None:
                continue
            size = box.size()
            ratio = int(size[0] * 100 / baseSize[0])
            option = ""
            if index != childs[target.index_][-1]:
                option = "margin-right: 5px; "
            print(".box%d { width: %d%%; color: #404040; background-color: %s; %s}" % (box.index_, ratio, colorString(color), option))
            stack.append(box)
            break
    if 0 < len(childs[target.index_]):
        option = "justify-content: center; " 
        if root == target:
            option = "flex-flow: column; width: %dpx;" % root.size()[0] 
        print(".box%d { display: flex; padding: 5px; %s}" % (target.index_, option))

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
    if 0 == len(childs[target.index_]):
        print("<article>")
        print("<h1>box%d</h1>" % target.index_)
        print("</article>")
    stack.append("</div>")
    for index in reversed(childs[target.index_]):
        for group in groups.values():
            box = group.find(index)
            if box is None:
                continue
            stack.append(box)
            break

print("</body>")
print("</html>")
sys.exit()

# debug print
for color, group in groups.items():
    if not group.empty():
        print("color=%s" % str(color))
        group.dump()


