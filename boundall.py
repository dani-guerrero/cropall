#! /usr/bin/env python2

#README:
#this script needs
#1.  python 2.7 (or at least < 3) https://www.python.org/downloads/release/python-278/
#       also python-tk and python-imaging-tk
#2.  imagemagick http://www.imagemagick.org/script/binary-releases.php#windows
#3.  both added to PATH http://stackoverflow.com/questions/6318156/adding-python-path-on-windows-7

#4. If "import Image" fails below, do this...
#   install pip http://stackoverflow.com/questions/4750806/how-to-install-pip-on-windows
#   run "pip install Pillow"
#   or on linux install python-pillow and python-pillow-tk http://stackoverflow.com/questions/10630736/no-module-named-image-tk

#you may change the below self-explanatory variables

#select input images from current directory
image_extensions = [".jpg", ".png", ".bmp"]

#directory to put output images (created automatically in current directory)
out_directory = ""

#after cropping, will resize down until the image firs in these dimensions. set to 0 to disable
resize_width = 0
resize_height = 0

#uses low resolution to show crop (real image will look better than preview)
fast_preview = True

#if the above is False, this controls how accurate the left hand preview image is
antialiase_original_preview = True

#ignores check to see if maintaining the apsect ratio perfectly is possible
allow_fractional_size = False

#selection mode: can be 'click-drag' or 'scroll'
#scroll: you select a resizable rectangle of a fixed aspect ratio that can be resized using the scroll wheel
#click-drag: you click at the top left corner of your selection, then drag down to the bottom-right corner and release. hold shift during dragging to move the entire selection.
initial_selection_mode = 'click-drag'

#displays rule-of-third guidelines
show_rule_of_thirds = False

#color of the selection box
selection_box_color = 'yellow'

#whether the AR should be fixed by default
default_fix_ratio = False





def pause():
    raw_input("Press Enter to continue...")

try:
    import os, sys
    print(sys.version)

    from distutils import spawn
    convert_path = spawn.find_executable("convert")
    if convert_path:
        print("Found 'convert' at", convert_path)
    else:
        raise EnvironmentError("Could not find ImageMagick's 'convert'. Is it installed and in PATH?")

    print("Importing libraries...")

    print("> Tkinter")
    import tkinter
    from tkinter import *
    from tkinter import Frame
    print("> subprocess")
    import subprocess
    print("> tkFileDialog")
    from tkinter import filedialog
    print("> shutil")
    import shutil
    print("> Image")
    try:
        from PIL import Image
    except ImportError:
        import Image
    print("> ImageOps")
    try:
        from PIL import ImageOps
    except ImportError:
        import ImageOps
    print("> ImageTk")
    try:
        from PIL import ImageTk
    except ImportError:
        import ImageTk
    print("Done")
except Exception as e:
    #because windows closes the window
    print(e)
    pause()
    raise e

if resize_height == 0:
    resize_width = 0
if resize_width < -1 or resize_height < -1:
    print("Note: resize is invalid. Not resizing.")
    pause()
    resize_width = 0

def clamp(x, a, b):
    return min(max(x, a), b)

# open a SPIDER image and convert to byte format
#im = Image.open(allImages[0])
#im = im.resize((250, 250), Image.ANTIALIAS)

#root = Tkinter.Tk()
# A root window for displaying objects

# Convert the Image object into a TkPhoto object
#tkimage = ImageTk.PhotoImage(im)

#Tkinter.Label(root, image=tkimage).pack()
# Put it in the display window

class MyApp(Tk):
    def getImages(self, dir):
        print("Scanning " + dir)
        allImages = []
        for i in os.listdir(dir):
            b, e = os.path.splitext(i)
            if e.lower() not in image_extensions: continue
            allImages += [i]
        return allImages

    def __init__(self, bounds):
        Tk.__init__(self)

        self.bounds=bounds
        self.wm_title("cropall")

        # Try directory given on the command line or the current directory
        if len(sys.argv) > 1:
            self.inDir = sys.argv[1]
        else:
            self.inDir = os.getcwd()

        infiles = self.bounds['file']

        print("Initializing GUI")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.geometry("1024x512")
        #self.resizable(0,0)

        self.files = infiles

        self.preview = None

        self.item = None

        self.mouse_down_coord = (0, 0)
        self.mouse_move_coord = (0, 0)

        # "click-drag" selection corners (top left and bottom right)
        row = self.bounds.iloc[0]
        img = Image.open(self.inDir+row['file'])
        self.imageOrig = img
        self.imageOrigSize = (img.size[0], img.size[1])
        imw = self.imageOrigSize[0]
        imh = self.imageOrigSize[1]
        self.imagePhoto = ImageTk.PhotoImage(img)
        prevw = self.imagePhoto.width()
        prevh = self.imagePhoto.height()
        self.selection_tl_x = row['xtl']
        self.selection_tl_y = row['ytl']
        self.selection_br_x = row['xbr']
        self.selection_br_y = row['ybr']

        self.shift_pressed = False

        self.controls = Frame(self)
        self.controls.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.buttons = []
        self.selection_mode = StringVar()
        self.selection_mode.set(initial_selection_mode)
        self.selection_mode_dropdown = OptionMenu(self.controls, self.selection_mode, 'click-drag')
        self.selection_mode_dropdown.grid(row=0, column=0, sticky="nsew")

        self.inputs = []

        self.restrictRatio = IntVar()
        self.inputs += [Checkbutton(self.controls, text="Fix Aspect Ratio", variable=self.restrictRatio)]
        self.inputs[-1].grid(row=0, column=1, sticky="nsew")

        self.aspect = (StringVar(), StringVar())
        self.aspect[0].set("RatioX")
        self.aspect[1].set("RatioY")
        self.inputs += [Entry(self.controls, textvariable=self.aspect[0])]
        self.inputs[-1].grid(row=0, column=2, sticky="nsew")
        self.inputs += [Entry(self.controls, textvariable=self.aspect[1])]
        self.inputs[-1].grid(row=0, column=3, sticky="nsew")

        self.buttons += [Button(self.controls, text="Prev", command=self.previous)]
        self.buttons[-1].grid(row=0, column=4, sticky="nsew")
        self.buttons += [Button(self.controls, text="Next", command=self.next)]
        self.buttons[-1].grid(row=0, column=5, sticky="nsew")
        self.buttons[-1].grid(row=0, column=6, sticky="nsew")
        self.buttons[-1].grid(row=0, column=7, sticky="nsew")
        self.buttons[-1].grid(row=0, column=8, sticky="nsew")

        self.restrictSizes = IntVar()
        self.inputs += [Checkbutton(self.controls, text="Perfect Pixel Ratio", variable=self.restrictSizes)]
        self.inputs[-1].grid(row=0, column=8, sticky="nsew")

        self.imageLabel = Canvas(self, highlightthickness=0)
        self.imageLabel.grid(row=0, column=0, sticky='nw', padx=0, pady=0)
        self.c = self.imageLabel

        self.previewLabel = Label(self, relief=FLAT, borderwidth=0)
        self.previewLabel.grid(row=0, column=1, sticky='nw', padx=0, pady=0)

        self.restrictSizes.set(0 if allow_fractional_size else 1)
        self.restrictRatio.set(1 if default_fix_ratio else 0)

        self.aspect[0].trace("w", self.on_aspect_changed)
        self.aspect[1].trace("w", self.on_aspect_changed)
        self.restrictSizes.trace("w", self.on_option_changed)
        self.restrictRatio.trace("w", self.on_aspect_changed)
        self.bind('e', self.del_next)
        self.bind('d', self.next)
        self.bind('a', self.previous)
        self.c.bind('<ButtonPress-1>', self.on_mouse_down)
        self.c.bind('<B1-Motion>', self.on_mouse_drag)
        self.c.bind('<ButtonRelease-1>', self.on_mouse_up)
        #self.c.bind('<Button-3>', self.on_right_click)
        self.bind('<KeyPress-Shift_L>', self.on_shift_press)
        self.bind('<KeyRelease-Shift_L>', self.on_shift_release)
        self.bind('<Escape>', self.remove_focus)

        self.current = 0
        self.load_imgfile(row['file'])

    def updateCropSize(self):
        if self.cropIndex <= 4:
            self.cropdiv = 8.0 / (9.0 - self.cropIndex)
        else:
            self.cropdiv = (1 + (self.cropIndex - 1) * 0.25)

    def getCropSize(self):
        self.updateCropSize()
        h = int(self.imageOrigSize[1] / self.cropdiv)
        w = int(self.imageOrigSize[1] * self.aspectRatio / self.cropdiv)
        if w > self.imageOrigSize[0]:
            w = int(self.imageOrigSize[0] / self.cropdiv)
            h = int(self.imageOrigSize[0] / (self.cropdiv * self.aspectRatio))
        #w = int(self.imageOrigSize[0] / self.cropdiv)
        return w, h

    def getRealBox(self):
        imw = self.imageOrigSize[0]
        imh = self.imageOrigSize[1]
        prevw = self.imagePhoto.width()
        prevh = self.imagePhoto.height()

        if (self.selection_mode.get() == 'click-drag'):
            top_left = (self.selection_tl_x*imw/prevw, self.selection_tl_y*imh/prevh)
            top_left = (max(top_left[0], 0), max(top_left[1], 0))
            bottom_right = (self.selection_br_x*imw/prevw, self.selection_br_y*imh/prevh)
            bottom_right = (max(top_left[0] + 1, min(bottom_right[0], imw)), max(top_left[1] + 1, min(bottom_right[1], imh)))
            w = bottom_right[0] - top_left[0]
            h = bottom_right[1] - top_left[1]

            # increase box to cover the selection, matching the aspect ratio
            if (self.restrictRatio.get() == 1):
                if (float(w)/float(h) > self.aspectRatio): # box is too wide -> increase height to match aspect
                    h = w / self.aspectRatio
                    if self.mouse_move_coord[1] > self.mouse_down_coord[1]:
                        bottom_right = (bottom_right[0], top_left[1] + h)
                    else:
                        top_left = (top_left[0], bottom_right[1] - h)
                else: # box is too tall -> increase width to match aspect
                    w = h * self.aspectRatio
                    if self.mouse_move_coord[0] > self.mouse_down_coord[0]:
                        bottom_right = (top_left[0] + w, bottom_right[1])
                    else:
                        top_left = (bottom_right[0] - w, top_left[1])

            """
            # reduce box to fit within selection, matching the aspect ratio
            if (self.restrictRatio.get() == 1):
                if (float(w)/float(h) > self.aspectRatio): # box is too wide -> reduce width to match aspect
                    w = h * self.aspectRatio
                    if self.mouse_move_coord[0] > self.mouse_down_coord[0]:
                        bottom_right = (top_left[0] + w, bottom_right[1])
                    else:
                        top_left = (bottom_right[0] - w, top_left[1])
                else: # box is too tall -> reduce height to match aspect
                    h = w / self.aspectRatio
                    if self.mouse_move_coord[1] > self.mouse_down_coord[1]:
                        bottom_right = (bottom_right[0], top_left[1] + h)
                    else:
                        top_left = (top_left[0], bottom_right[1] - h)
            """

            box = (int(round(top_left[0])), int(round(top_left[1])), int(round(bottom_right[0])), int(round(bottom_right[1])))

        return box

    def getPreviewBox(self):
        imw = self.imageOrigSize[0]
        imh = self.imageOrigSize[1]
        prevw = self.imagePhoto.width()
        prevh = self.imagePhoto.height()
        bbox = self.getRealBox()
        bbox = (bbox[0]*prevw/imw, bbox[1]*prevh/imh, bbox[2]*prevw/imw, bbox[3]*prevh/imh)
        return (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))


    def previous(self, event=None):
        try:
            bbox = self.getRealBox()
            self.bounds.loc[self.bounds.file == self.currentName,'xtl'] = bbox[0]
            self.bounds.loc[self.bounds.file == self.currentName,'ytl'] = bbox[1]
            self.bounds.loc[self.bounds.file == self.currentName,'xbr'] = bbox[2]
            self.bounds.loc[self.bounds.file == self.currentName,'ybr'] = bbox[3]
        except:
            pass
        self.current -= 1
        self.current = (self.current + len(self.files)) % len(self.files)
        self.load_imgfile(self.files[self.current])

    def next(self, event=None):
        bbox = self.getRealBox()
        self.bounds.loc[self.bounds.file == self.currentName,'xtl'] = bbox[0]
        self.bounds.loc[self.bounds.file == self.currentName,'ytl'] = bbox[1]
        self.bounds.loc[self.bounds.file == self.currentName,'xbr'] = bbox[2]
        self.bounds.loc[self.bounds.file == self.currentName,'ybr'] = bbox[3]
        self.current += 1
        self.current = (self.current + len(self.files)) % len(self.files)
        self.load_imgfile(self.files[self.current])

    def del_next(self, event=None):
        self.bounds = self.bounds.loc[self.bounds.file!=self.currentName]
        self.files = self.bounds['file']
        print("Image Deleted")
        self.next()

    def load_imgfile(self, filename):
        self.currentName = filename
        print(self.currentName)
        fullFilename = os.path.join(self.inDir, filename)
        print("Loading " + fullFilename)
        img = Image.open(fullFilename)

        self.imageOrig = img
        self.imageOrigSize = (img.size[0], img.size[1])
        print("Image is " + str(self.imageOrigSize[0]) + "x" + str(self.imageOrigSize[1]))

        basewidth = 512
        wpercent = (basewidth/float(img.size[0]))
        hsize = int((float(img.size[1])*float(wpercent)))
        if fast_preview:
            #does NOT create a copy so self.imageOrig is the same as self.image
            img.thumbnail((basewidth,hsize), Image.NEAREST)
        else:
            if antialiase_original_preview:
                img = img.resize((basewidth,hsize), Image.ANTIALIAS)
            else:
                img = img.copy()
                img.thumbnail((basewidth,hsize), Image.NEAREST)
        self.image = img
        print("Resized preview")

        self.configure(relief='flat', background='gray')

        self.imagePhoto = ImageTk.PhotoImage(self.image)
        self.imageLabel.configure(width=self.imagePhoto.width(), height=self.imagePhoto.height())
        self.imageLabel.create_image(0, 0, anchor=NW, image=self.imagePhoto)

        self.previewPhoto = ImageTk.PhotoImage(self.image)
        self.previewLabel.configure(image=self.previewPhoto)

        self.item = None

        self.verti_aux_item = None
        self.horiz_aux_item = None


        row = (self.bounds[bounds.file==self.currentName])
        print(row)
        imw = self.imageOrigSize[0]
        imh = self.imageOrigSize[1]
        prevw = self.imagePhoto.width()
        prevh = self.imagePhoto.height()
        if (not row.empty):
            self.selection_tl_x = int(row['xtl']) * prevw/imw
            self.selection_tl_y = int(row['ytl']) * prevh/imh
            self.selection_br_x = int(row['xbr']) * prevw/imw
            self.selection_br_y = int(row['ybr']) * prevh/imh
        self.on_aspect_changed(None, None, None) #update aspect ratio with new image size

    def update_box(self, widget):
        bbox = self.getPreviewBox()
        #bbox = (widget.canvasx(bbox[0]), widget.canvasy(bbox[1]), widget.canvasx(bbox[2]), widget.canvasy(bbox[3]))

        if self.item is None:
            self.item = widget.create_rectangle(bbox, outline=selection_box_color)
        else:
            widget.coords(self.item, *bbox)

        if (show_rule_of_thirds):
            horiz_bbox = (bbox[0], bbox[1] + (bbox[3] - bbox[1]) / 3, bbox[2], bbox[3] - (bbox[3] - bbox[1]) / 3)
            verti_bbox = (bbox[0] + (bbox[2] - bbox[0]) / 3, bbox[1], bbox[2] - (bbox[2] - bbox[0]) / 3, bbox[3])
            if self.horiz_aux_item is None:
                    self.horiz_aux_item = widget.create_rectangle(horiz_bbox, outline=selection_box_color)
            else:
                    widget.coords(self.horiz_aux_item, *horiz_bbox)
            if self.verti_aux_item is None:
                    self.verti_aux_item = widget.create_rectangle(verti_bbox, outline=selection_box_color)
            else:
                    widget.coords(self.verti_aux_item, *verti_bbox)

    def update_preview(self, widget):
        if self.item:
            #get a crop for the preview
            #box = tuple((int(round(v)) for v in widget.coords(self.item)))
            box = self.getRealBox()
            pbox = self.getPreviewBox()
            if fast_preview:
                preview = self.image.crop(pbox) # region of interest
            else:
                preview = self.imageOrig.crop(box) # region of interest

            #add black borders for correct aspect ratio
            #if preview.size[0] > 512:
            preview.thumbnail(self.image.size, Image.ANTIALIAS) #downscale to preview rez
            paspect = preview.size[0]/float(preview.size[1])
            aspect = self.image.size[0]/float(self.image.size[1])
            if paspect < aspect:
                bbox = (0, 0, int(preview.size[1] * aspect), preview.size[1])
            else:
                bbox = (0, 0, preview.size[0], int(preview.size[0] / aspect))
            preview = ImageOps.expand(preview, border=((bbox[2]-preview.size[0])//2, (bbox[3]-preview.size[1])//2))

            #resize to preview rez (if too small)
            self.preview = preview.resize(self.image.size, Image.ANTIALIAS)
            self.previewPhoto = ImageTk.PhotoImage(self.preview)
            self.previewLabel.configure(image=self.previewPhoto)

            print(str(box[2]-box[0])+"x"+str(box[3]-box[1])+"+"+str(box[0])+"+"+str(box[1]))

    def remove_focus(self, event=None):
            self.focus()

    def on_aspect_changed(self, event, var1, var2):
        if (self.restrictRatio.get() == 1):
            try:
                x = float(self.aspect[0].get())
                y = float(self.aspect[1].get())
                if x < 0 or y < 1:
                    raise ZeroDivisionError()
                self.aspectRatio = x / y
            except (ZeroDivisionError, ValueError) as e:
                self.aspectRatio = float(self.imageOrigSize[0])/float(self.imageOrigSize[1])
        else:
            self.aspectRatio = float(self.imageOrigSize[0])/float(self.imageOrigSize[1])
        self.update_box(self.imageLabel)
        self.update_preview(self.imageLabel)

    def on_option_changed(self, event, var1, var2):
        global allow_fractional_size
        allow_fractional_size = (self.restrictSizes.get() == 0)


    def on_mouse_down(self, event):
        self.remove_focus()

        self.mouse_down_coord = (event.x, event.y)
        self.mouse_move_coord = (event.x, event.y)

        self.x = event.x
        self.y = event.y

        self.update_box(event.widget)

    def on_mouse_drag(self, event):

        delta = (event.x - self.mouse_move_coord[0], event.y - self.mouse_move_coord[1])
        self.mouse_move_coord = (event.x, event.y)

        prevw = self.imagePhoto.width()
        prevh = self.imagePhoto.height()

        #click-drag selection
        if self.shift_pressed:
            move = [delta[0], delta[1]]
            move[0] = max(self.selection_tl_x + move[0], 0) - self.selection_tl_x
            move[0] = min(self.selection_br_x + move[0], prevw) - self.selection_br_x
            move[1] = max(self.selection_tl_y + move[1], 0) - self.selection_tl_y
            move[1] = min(self.selection_br_y + move[1], prevw) - self.selection_br_y
            self.selection_tl_x += move[0]
            self.selection_tl_y += move[1]
            self.selection_br_x += move[0]
            self.selection_br_y += move[1]
        else:
            self.selection_tl_x = min(self.mouse_down_coord[0], event.x)
            self.selection_tl_y = min(self.mouse_down_coord[1], event.y)
            self.selection_br_x = max(self.mouse_down_coord[0], event.x) + 1
            self.selection_br_y = max(self.mouse_down_coord[1], event.y) + 1

        self.x = event.x
        self.y = event.y

        self.update_box(event.widget)

    def on_mouse_up(self, event):
        self.update_preview(event.widget)

    def on_shift_press(self, event):
        self.shift_pressed = True

    def on_shift_release(self, event):
        self.shift_pressed = False

import pandas as pd
bounds = pd.read_csv('bounds.csv')
app =  MyApp(bounds)
app.mainloop()
print(app.bounds)
app.bounds.to_csv('bounds_tmp.csv', index=False)
shutil.move('bounds_tmp.csv','bounds.csv')
