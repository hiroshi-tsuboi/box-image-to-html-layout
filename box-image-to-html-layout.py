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
        self.flow_ = 0
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
    def sort(self):
        if len(self.childs_) <= 1:
            return
        self.childs_.sort(key=lambda x: x.mini_[1])
        for i in range(len(self.childs_) - 1):
            if self.childs_[i + 1].mini_[1] <= self.childs_[i].maxi_[1]:
                self.childs_.sort(key=lambda x: x.mini_[0])
                return
        self.flow_ = 1

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
        for target in self.boxes_:
            target.sort()
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
            print("scale = %s" % str(self.scale_))

def colorToString(color):
    r = "#"
    for i in range(3):
        r += "%02X" % color[i]
    return r

def stringToColor(string):
    r = []
    for i in range(3):
        x = string[1+i*2:1+i*2+2]
        r.append(int(x, 16))
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
delimiterIndex = filename.rfind('/')
if 0 <= delimiterIndex:
    configFilename = filename[:delimiterIndex+1] + configFilename
config = Config(configFilename, debug)

# create box from image

groups = {}
boxIndex = 1

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

# sort & compute margin left and top
for group in groups.values():
    group.finalize()

# find root
roots = []
for group in groups.values():
    for box in group.boxes_:
        if box.parent_ is None:
            roots.append(box)
if 1 < len(roots):
    mini = copy.copy(roots[0].mini_)
    maxi = copy.copy(roots[0].maxi_)
    for box in root[1:]:
        for i in range(2):
            if box.mini_[i] < mini[i]:
                mini[i] = box.mini_[i]
            if maxi[i] < box.maxi_[i]:
                maxi[i] = box.maxi_[i]
    # create root
    root = Box(mini, maxi, 0, (0,0,0))
    for child in roots:
        child.parent_ = root
        root.childs_.append(child)
    root.sort()
    roots = [root]

# render html
if not debug:
    print("<!DOCTYPE html>")
    print("<html>")
    print("<head>")
    print('<style type="text/css">')

    stack = [roots[0]]
    while 0 < len(stack):
        target = stack.pop()
        option = ""
        if 1 == target.flow_:
            #option += "float: none; "
            pass
        else:
            option += "float: left; "
        size = target.size()
        option += target.margin()
        print(".box%d { width: %dpx; height: %dpx; color: #404040; background-color: %s; %s}" % (target.index_, size[0], size[1], colorToString(target.color_), option))

        for child in target.childs_:
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
        print("color = %s" % colorToString(color))
        #print("%s" % (stringToColor(colorToString(color))))
        group.dump()


