from array import array
import os
from math import floor, sqrt

from random import choice, randint

from kivy.app import App
from kivy.atlas import Atlas
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.graphics import Rectangle
from kivy.graphics.texture import Texture
from kivy.properties import NumericProperty, ObjectProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget

#  http://finalbossblues.com/timefantasy/

# ATLAS_FILE = '{}/assets/kenny/medievalrts/medievalrts.atlas'.format(os.getcwd())
# ATLAS_TREE_FILE = '{}/asset_manipulation/output/trees.atlas'.format(os.getcwd())
ATLAS_FILE = '{}/trees.atlas'.format(os.getcwd())
ATLAS_CHAR_FILE = '{}/characters.atlas'.format(os.getcwd())
BUFFERFMT = 'ubyte'


Builder.load_string("""
<AtlasLayout>:
    size_hint: 1,1
    pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            
    RenderLayout:
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        size_hint: None, None
        size: 576, 576
        
        RenderWidget:
            id: render_widget
            size_hint: None, None
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            
    Label:
        text:'WASD to move'
        size_hint: None, None
        size: 200, 50
        pos_hint: {'x':0, 'top':1.0}
                
    Button: 
        text: 'Reset Generation'
        size_hint: None, None
        size: 175, 75
        pos_hint: {'x':0.0, 'y':0}
        on_release: render_widget.reset_generation()
        
    # Button: 
    #     text: 'Update Tiles'
    #     size_hint: None, None
    #     size: 100, 100
    #     pos_hint: {'center_x':0.5, 'y':0}
    #     on_release: render_widget.switch_update_tiles()
        
    # Button:
    #     text: 'Decrease viewpane'
    #     size_hint: None, None
    #     size: 100, 75
    #     pos: 0, 100
    #     on_release: render_widget.resize(-32)
    # Button:
    #     text: 'Increase Viewpane'
    #     size_hint: None, None
    #     size: 100, 75
    #     pos: 0,175
    #     on_release: render_widget.resize(32)
        
       
    
""")


class Entity:

    def __init__(self, name='', x=-100, y=-100):
        self.x = x
        self.y = y
        self.name = name

    def __repr__(self):
        return "{} at ({}, {})".format(self.name, self.x, self.y)


class AtlasLayout(FloatLayout):
    pass


class RenderLayout(FloatLayout, StencilView):
    pass


class RenderWidget(Widget):
    data = {}  # dict of tile names pointing to a list of bytecode for each tile image
    data_size = {}  # dict of tile names pointing to a tuple of the image size

    tree_data = {}  # dict of tile names pointing to a list of bytecode for each tree tile image
    tree_data_size = {}  # dict of tile names pointing to a tuple of the tree image size

    char_data = {}  # dict of char names pointing to bytecode for each character image

    tile_enum = {}  # dict of integers pointing to a tile name
    entities = []  # list of NPCs

    tex = None  # texture layer for background tiles
    fov_tex = None  # texture layer containing FOV shadowing/lightning
    entities_tex = None  # texture layer containing entities
    tile_clock = None  # clock for constantly updating texture

    map = None  # map 2d array for tile integers
    map_clock = None  # map 2d array for what cycle image index each tile is on

    viewpane_center_x = NumericProperty(0)  # center_x position for viewpane
    viewpane_center_y = NumericProperty(0)  # center_y position for viewpane

    tile_size = 32  # size of each tile, pixels
    player_x = NumericProperty(0)  # x-position of player
    player_y = NumericProperty(0)  # y-position of player
    player_speed = 16  # pixels per tick

    pressed_keys = {97: False,
                    100: False,
                    115: False,
                    119: False,
                    113: False,
                    101: False}

    def __init__(self, **kwargs):
        super(RenderWidget, self).__init__(**kwargs)
        self.size = 608, 608
        self.tile_size = 32
        self.atlas = Atlas(ATLAS_FILE)
        self.char_atlas = Atlas(ATLAS_CHAR_FILE)
        self.map_width = 50
        self.map_height = 50

        ind = -1
        for name, tex in self.atlas.textures.items():

            if '_' in name:
                tile_name, tile_number = name.split('_')
            else:
                tile_name, tile_number = name, '0'

            tex.flip_vertical()
            if self.data.get(tile_name):
                self.data[tile_name].append(tex.pixels)
            else:
                ind += 1
                self.data[tile_name] = [tex.pixels]
            self.data_size[tile_name] = tex.size

            if not self.tile_enum.get(ind):
                self.tile_enum[ind] = tile_name

        # Entity Textures
        for name, tex in self.char_atlas.textures.items():
            tex.flip_vertical()
            self.char_data[name] = tex.pixels
            # print(name, tex)

        # for name, size in self.data_size.items():
        #     print('\n{} size: {}'.format(name, size))

        self.initialize_tiles()
        Window.bind(on_key_down=self._keydown)
        Window.bind(on_key_up=self._keyup)
        Clock.schedule_interval(self.check_for_keys, 60 ** -1)
        self.tile_clock = Clock.schedule_interval(self.update_tiles, 60 ** -1)

    def on_player_x(self, instance, value):
        if self.player_x >= self.tile_size:
            self.viewpane_center_x -= 1
            self.player_x -= self.tile_size
        elif self.player_x <= -self.tile_size:
            self.viewpane_center_x += 1
            self.player_x += self.tile_size

    def on_player_y(self, instance, value):
        if self.player_y >= self.tile_size:
            self.viewpane_center_y -= 1
            self.player_y -= self.tile_size
        elif self.player_y <= -self.tile_size:
            self.viewpane_center_y += 1
            self.player_y += self.tile_size

    def check_for_keys(self, dt):
        if self.pressed_keys[115]:
        # if self.pressed_keys[115] and self.viewpane_center_y > 0:
            self.player_y += self.player_speed

        if self.pressed_keys[119]:
        # if self.pressed_keys[119] and self.viewpane_center_y < self.map_height - self.height // self.tile_size:
            self.player_y -= self.player_speed

        if self.pressed_keys[100]:
        # if self.pressed_keys[100] and self.viewpane_center_x < self.map_width - self.width // self.tile_size:
            self.player_x -= self.player_speed

        if self.pressed_keys[97]:
        # if self.pressed_keys[97] and self.viewpane_center_x > 0:
            self.player_x += self.player_speed

    def _keyup(self, keyboard, keycode, text, *args,**kwargs):
        pressed_key = keycode
        self.pressed_keys[pressed_key] = False

    def _keydown(self, keyboard, keycode, text, modifiers, *args, **kwargs):
        pressed_key = keycode
        self.pressed_keys[pressed_key] = True

    def on_viewpane_center_x(self, instance, value):
        pass

    def on_viewpane_center_y(self, instance, value):
        pass

    # def switch_update_tiles(self):
    #     # Clock for Updating all Texture Layers
    #     if self.tile_clock:
    #         self.tile_clock.cancel()
    #         self.tile_clock = None
    #     else:
    #         self.tile_clock = Clock.schedule_interval(self.update_tiles, 60 ** -1)

    def reset_generation(self):
        # Viewpane Center
        self.viewpane_center_x = randint(0, self.map_width - self.width // self.tile_size)
        self.viewpane_center_y = randint(0, self.map_height - self.height // self.tile_size)

        # Player Input Variables
        self.player_x = 0
        self.player_y = 0

        # Map Variables
        tile_indexes = len(self.data.keys()) - 1
        self.map = [[randint(0, tile_indexes) for i in range(self.map_width)] for j in range(self.map_height)]
        self.map_clock = [[0 for i in range(self.map_width)] for j in range(self.map_height)]

        # Entities
        self.entities = []
        char_names = list(self.char_data.keys())
        avg = (self.map_width + self.map_height) // 2
        self.entities = [Entity(name=choice(char_names),
                                x=randint(0, self.map_width-1) * self.tile_size,
                                y=randint(0, self.map_height-1) * self.tile_size) for i in range(avg)]
        # print('{} NPCs generated'.format(len(self.entities)))

    def initialize_tiles(self):
        # Create all Texture Layers
        self.tex = Texture.create(size=self.size, colorfmt='rgba')
        self.tex.mag_filter = 'nearest'
        self.fov_tex = Texture.create(size=self.size, colorfmt='rgba')
        self.fov_tex.mag_filter = 'nearest'
        self.entities_tex = Texture.create(size=self.size, colorfmt='rgba')
        self.entities_tex.mag_filter = 'nearest'

        # Initialize Texture Data
        size = self.width * self.height * 4
        buf = [255 for _ in range(size)]
        arr = array("B", buf)
        self.tex.blit_buffer(arr, colorfmt='rgba', bufferfmt=BUFFERFMT)
        self.reset_generation()
        self.render_canvas()

    def resize(self, new_size):
        self.size = self.width + new_size, self.height + new_size
        if self.parent:
            self.parent.size = self.width - self.tile_size, self.height - self.tile_size
        self.initialize_tiles(0)

    def update_tiles(self, dt):
        viewpane_width = self.width // self.tile_size
        viewpane_height = self.height // self.tile_size
        fov_dist = 8
        center = ((viewpane_width // 2) + (viewpane_height // 2)) // 2

        for x in range(self.viewpane_center_x + viewpane_width, self.viewpane_center_x - viewpane_width, -1):
            for y in range(self.viewpane_center_y + viewpane_height, self.viewpane_center_y - viewpane_height, -1):

                correct_x = x - self.viewpane_center_x  # normalize to 0 thru map width
                correct_y = y - self.viewpane_center_y
                pbuffer_size = (self.tile_size, self.tile_size)
                pbuffer_pos = (correct_x * self.tile_size, correct_y * self.tile_size)

                try:
                    1 // (abs(y + 1) + y + 1)  # check for negative numbers
                    1 // (abs(x + 1) + x + 1)
                    tile_integer = self.map[y][x]
                    tile_name = self.tile_enum[(floor(tile_integer))]
                    tile_clock_ind = floor(self.map_clock[y][x])
                    pbuffer = self.data[tile_name][tile_clock_ind]
                    pbuffer_size = self.data_size[tile_name]
                    pbuffer_pos = correct_x * self.tile_size + (self.tile_size - pbuffer_size[0]) // 2,  correct_y * self.tile_size + (self.tile_size - pbuffer_size[1]) // 2

                except ZeroDivisionError:
                    pbuffer = b'\x00\x00\x00\xff' * self.tile_size * self.tile_size  # default to black
                except IndexError:
                    try:
                        self.map_clock[y][x] = 0
                        pbuffer = self.data[tile_name][0]
                        pbuffer_size = self.data_size[tile_name]
                        pbuffer_pos = correct_x * self.tile_size + (self.tile_size - pbuffer_size[0]) // 2,  correct_y * self.tile_size + (self.tile_size - pbuffer_size[1]) // 2
                    except:
                        pbuffer = b'\x00\x00\x00\xff' * self.tile_size * self.tile_size  # default to black

                self.tex.blit_buffer(pbuffer=pbuffer,
                                     size=pbuffer_size,
                                     pos=pbuffer_pos,
                                     colorfmt='rgba',
                                     bufferfmt=BUFFERFMT
                                     )

                # FOV/Shadow Texture
                if self.calculate_distance(correct_x, correct_y, center, center) > fov_dist:
                    pbuffer = b'\x00\x00\x00\x7f' * self.tile_size * self.tile_size  # place (0, 0, 0, 127) shadow
                    self.fov_tex.blit_buffer(pbuffer=pbuffer,
                                             size=(self.tile_size, self.tile_size),
                                             pos=(correct_x * self.tile_size,
                                                  correct_y * self.tile_size),
                                             colorfmt='rgba',
                                             bufferfmt=BUFFERFMT
                                     )
        self.map_clock = [[self.map_clock[j][i] + 0.025 for i in range(self.map_width)] for j in range(self.map_height)]

        # Place Entities
        # render_entities = []
        render_entities = [e for e in self.entities \
                           if self.calculate_distance((e.x // self.tile_size) - self.viewpane_center_x, (e.y // self.tile_size) - self.viewpane_center_y, center, center) <= fov_dist]

        # Reset Texture
        self.entities_tex.blit_buffer(pbuffer= b'\x00\x00\xff\x00' * self.width * self.height,
                                      size=self.size,
                                      pos=(0, 0),
                                      colorfmt='rgba',
                                      bufferfmt=BUFFERFMT)

        for e in render_entities:
            self.entities_tex.blit_buffer(pbuffer=self.char_data[e.name],
                                          size=(self.tile_size, self.tile_size),
                                          pos=(e.x - (self.viewpane_center_x * self.tile_size), e.y - (self.viewpane_center_y * self.tile_size)),
                                          colorfmt='rgba',
                                          bufferfmt=BUFFERFMT)

        self.render_canvas()

    @staticmethod
    def calculate_distance(x1, y1, x2, y2):
        return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def render_canvas(self):
        self.canvas.clear()
        with self.canvas:
            # Background Tiles
            Rectangle(texture=self.tex, size=self.size, pos=(self.x + self.player_x, self.y + self.player_y))

            # Entities
            Rectangle(texture=self.entities_tex, size=self.size, pos=(self.x + self.player_x, self.y + self.player_y))

            # FOV
            Rectangle(texture=self.fov_tex, size=self.size, pos=(self.x + self.player_x, self.y + self.player_y))


class RendererApp(App):
    def build(self):
        return AtlasLayout()


if __name__ == '__main__':
    RendererApp().run()
