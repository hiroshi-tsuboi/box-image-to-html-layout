import sys
import json
import copy
from PIL import Image

#

class Margin():
    def __init__(self):
        self.leftop_ = [sys.maxsize, sys.maxsize]
    def clear(self):
        self.leftop_ = [0, 0]
    def update(self, i, x):
        self.leftop_[i] = min(self.leftop_[i], x)
    def string(self):
        r = ""
        substr = ("left", "top")
        for i in range(2):
            if self.leftop_[i] <= 0 or self.leftop_[i] == sys.maxsize:
                continue
            r += "margin-%s: %dpx; " % (substr[i], self.leftop_[i])
        return r

class Box():
    def __init__(self, mini, maxi, index, color):
        self.mini_ = copy.copy(mini)
        self.maxi_ = copy.copy(maxi)
        self.index_ = index
        self.parent_ = None
        self.childs_ = []
        self.margin_ = Margin()
        self.color_ = copy.copy(color)
        self.flow_ = 0
        size = self.size()
        self.area_ = size[0] * size[1]
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

        print("index=%d color=%s mini=(%d,%d) maxi=(%d,%d) parent=%d margin=%s" % (self.index_, str(self.color_), self.mini_[0], self.mini_[1], self.maxi_[0], self.maxi_[1], parentIndex, str(self.margin_.leftop_)))
        if 0 < len(self.childs_):
            indices = []
            for child in self.childs_:
                indices.append(child.index_)
            print("\tchild(s) = %s" % str(indices))
    def sort(self):
        if len(self.childs_) <= 1:
            return
        self.childs_.sort(key=lambda x: x.mini_[1])
        for i in range(len(self.childs_) - 1):
            if self.childs_[i + 1].mini_[1] <= self.childs_[i].maxi_[1]:
                self.childs_.sort(key=lambda x: x.mini_[0])
                return
        self.flow_ = 1
    def merge(self, box, index):
        mini = [min(self.mini_[0], box.mini_[0]), min(self.mini_[1], box.mini_[1])]
        maxi = [max(self.maxi_[0], box.maxi_[0]), max(self.maxi_[1], box.maxi_[1])]
        return Box(mini, maxi, index, (0,0,0))

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
    def finalize(self):
        for target in self.boxes_:
            target.sort()
        for i in range(2):
            for target in self.boxes_:
                if target.parent_ is not None:
                    target.margin_.update(i, target.mini_[i] - target.parent_.mini_[i])
                for box in self.boxes_:
                    if box.maxi_[i] < target.mini_[i]:
                        target.margin_.update(i, target.mini_[i] - box.maxi_[i] + 1)
                for child in target.childs_:
                    for box in target.childs_:
                        if box.maxi_[i] < child.mini_[i]:
                            child.margin_.update(i, child.mini_[i] - box.maxi_[i] + 1)

class Config():
    def __init__(self, filename, debug):
        self.scale_ = [1]
        try:
            with open(filename, "r") as f:
                ctxt = json.load(f)
                if "scale" in ctxt:
                    self.scale_.clear()
                    for x in ctxt["scale"]:
                        self.scale_.append(float(x))
        except:
            print("failed to open %s" % filename)

        if len(self.scale_) == 1:
            self.scale_.append(self.scale_[0])

        if debug:
            #print("scale = %s" % str(self.scale_))
            pass

def colorToString(color):
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

# load config.json
configFilename = "config.json"
basePathIndex = filename.rfind('/')
if 0 <= basePathIndex:
    configFilename = filename[:basePathIndex+1] + configFilename
config = Config(configFilename, debug)

# create box from image

groups = {}
boxIndex = 1

for y in range(image.size[1]):
    for x in range(image.size[0]):
        pixel = image.getpixel((x, y))

        # ignore alpha
        color = (pixel[0], pixel[1], pixel[2])

        if color in groups:
            if groups[color].inside((x, y)):
                continue
        else:
            groups[color] = Group()

        # extent

        mini = [x, y]
        maxi = [x, y]

        for i in range(2):
            t = [x, y]
            for j in range(mini[i] + 1, image.size[i]):
                t[i] = j
                pixel = image.getpixel((t[0], t[1]))
                if color != (pixel[0], pixel[1], pixel[2]):
                    break
                maxi[i] = j

        # discard thin box
        if (maxi[0] - mini[0]) <= 1 or (maxi[1] - mini[1]) <= 1:
            continue

        groups[color].add(mini, maxi, boxIndex, color)
        boxIndex += 1

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

# merge box
roots = []
for group in groups.values():
    for box in group.boxes_:
        if box.parent_ is None:
            roots.append(box)
while 1 < len(roots):
    roots.sort(key=lambda x: x.area_)
    nboxes = []
    for y in roots:
        cboxes = [y]
        for x in roots:
            if x == y:
                continue
            z = x.merge(y, boxIndex)
            #print("%d : %d = %d(%d) + %d(%d)" % (z.area_, x.area_ + y.area_, x.area_, x.index_, y.area_, y.index_))
            if z.area_ == (x.area_ + y.area_):
                cboxes.append(x)
        if 1 < len(cboxes):
            z = copy.copy(cboxes[0])
            for box in cboxes[1:]:
                z = z.merge(box, boxIndex)
            for box in cboxes:
                box.parent_ = z
                z.childs_.append(box)
                box.margin_.clear()
                roots.remove(box)
            z.sort()
            nboxes.append(z)
            #z.dump()
            boxIndex += 1
            break
    if 0 == len(nboxes):
        break
    roots.append(nboxes[0])

# sort & compute margin left and top
for group in groups.values():
    group.finalize()

# render html
if not debug:
    print("<!DOCTYPE html>")
    print("<html>")
    print("<head>")
    print('<style type="text/css">')

    stack = [roots[0]]
    while 0 < len(stack):
        target = stack.pop()
        option = "box-sizing: border-box; "
        if 1 == target.flow_:
            #option += "float: none; "
            option += "display: flex; flex-direction: column; "
            pass
        else:
            #option += "float: left; "
            option += "display: flex; flex-direction: row; "
        size = target.size()
        option += target.margin_.string()
        print(".box%d { width: %dpx; height: %dpx; color: #404040; background-color: %s; %s}" % (target.index_, size[0], size[1], colorToString(target.color_), option))

        for child in reversed(target.childs_):
            stack.append(child)

    print("</style>")
    print("</head>")
    print("<body>")

    stack = [roots[0]]
    while 0 < len(stack):
        target = stack.pop()
        if type(target) is str:
            print(target)
            continue
        print('<div class="box%d">' % target.index_)
        if 0 == len(target.childs_):
            print("<article>")
            print("box%d" % target.index_)
            print("</article>")
        stack.append("</div>")
        for child in reversed(target.childs_):
            stack.append(child)

    print("</body>")
    print("</html>")
    sys.exit()

# debug print
stack = roots
while 0 < len(stack):
    target = stack.pop()
    target.dump()
    for child in reversed(target.childs_):
        stack.append(child)

