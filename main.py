from array import array
import os
from math import floor, sqrt

from random import choice, randint

from kivy.app import App
from kivy.atlas import Atlas
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.graphics import Callback, Color, Rectangle
from kivy.graphics.opengl import glBlendFunc, GL_SRC_ALPHA, GL_ONE, GL_ZERO, GL_SRC_COLOR, GL_ONE_MINUS_SRC_COLOR, GL_ONE_MINUS_SRC_ALPHA, GL_DST_ALPHA, GL_ONE_MINUS_DST_ALPHA, GL_DST_COLOR, GL_ONE_MINUS_DST_COLOR
from kivy.graphics.texture import Texture
from kivy.graphics.context_instructions import PopMatrix, PushMatrix, Rotate, Scale, Translate
from kivy.properties import NumericProperty, ObjectProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget

# from kivyparticle.kivyparticle import ParticleSystem as KivyParticleSystem

from ca import CellularAutomata

ATLAS_TREE_FILE = '{}/assets/trees.atlas'.format(os.getcwd())
ATLAS_FILE = '{}/assets/grass.atlas'.format(os.getcwd())
ATLAS_CHAR_FILE = '{}/assets/characters.atlas'.format(os.getcwd())
BUFFERFMT = 'ubyte'


Builder.load_string("""
<AtlasLayout>:
    size_hint: 1,1
    pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            
    RenderLayout:
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        size_hint: None, None
        size: 592, 592
        
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
        text: 'Reset Genration'
        size_hint: None, None
        size: 175, 75
        pos_hint: {'x':0.0, 'y':0}
        on_release: render_widget.reset_generation()
        
    # Button: 
    #     text: 'Update Tiles'
    #     size_hint: None, None
    #     size: 100, 100
    #     pos_hint: {'center_x':0.5, 'y':0}
    #     on_release: render_widget.generate_particle()
        
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


class ParticleSystem:
    particles = []
    positions = []


class Particle:
    texture = None
    x = -100
    y = -100
    name = ''
    angle = 0
    scale = 1

    def __init__(self, x,  y, name, scale, texture):
        self.x = x
        self.y = y
        self.name = name
        self.texture = texture
        self.scale = scale
        self.scale_direction = 1

    def update(self, dt):
        # Size
        # self.scale += dt * self.scale_direction
        # if self.scale > 1.1:
        #     self.scale_direction = -1
        # elif self.scale < 0.9:
        #     self.scale_direction = 1

        # Rotation of Particle
        self.angle += dt * 500
        if self.angle > 360:
            self.angle = 0


class Entity:

    def __init__(self, name='', x=-100, y=-100):
        self.x = x
        self.y = y
        self.name = name

    def __repr__(self):
        return "{} at ({}, {})".format(self.name, self.x, self.y)


class AtlasLayout(FloatLayout):
    pass


class RenderLayout(StencilView):
    kivy_particle = None

    def __init__(self, **kwargs):
        super(RenderLayout, self).__init__(**kwargs)
        # self.kivy_particle = KivyParticleSystem('demo/media/particle.pex')
        # self.add_widget(self.kivy_particle)

    # def on_touch_down(self, touch):
    #     if self.kivy_particle:
    #         self.kivy_particle.emitter_x = float(touch.x)
    #         self.kivy_particle.emitter_y = float(touch.y)
    #         self.kivy_particle.start()
    # 
    # def on_touch_move(self, touch):
    #     self.kivy_particle.emitter_x = float(touch.x)
    #     self.kivy_particle.emitter_y = float(touch.y)
    # 
    # def on_touch_up(self, touch):
    #     self.kivy_particle.stop(False)


class RenderWidget(Widget):
    data = {}  # dict of tile names pointing to a list of bytecode for each tile image
    data_size = {}  # dict of tile names pointing to a tuple of the image size
    blank_tex = None
    particle_tex = None
    player = None

    tree_data = {}  # dict of tile names pointing to a list of bytecode for each tree tile image
    tree_enum = {}

    char_data = {}  # dict of char names pointing to bytecode for each character image
    particles = []  # list of particles
    tile_enum = {}  # dict of integers pointing to a tile name
    entities = []  # list of NPCs
    foilage = []  # list of foilage
    cellular_automata = None

    tex = None  # texture layer for background tiles
    fov_tex = None  # texture layer containing FOV shadowing/lightning
    entities_tex = None  # texture layer containing entities
    tile_clock = None  # clock for constantly updating texture

    map = None  # map 2d array for tile integers
    map_clock = None  # map 2d array for what cycle image index each tile is on
    tree_map = None
    tree_clock = None

    viewpane_center_x = NumericProperty(0)  # center_x position for viewpane
    viewpane_center_y = NumericProperty(0)  # center_y position for viewpane

    tile_size = 32  # size of each tile, pixels
    player_x = NumericProperty(0)  # x-position of player
    player_y = NumericProperty(0)  # y-position of player
    player_speed = 8  # pixels per tick
    player_turn = True
    player_turn_speed = 0.01

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
        self.atlas_trees = Atlas(ATLAS_TREE_FILE)
        self.char_atlas = Atlas(ATLAS_CHAR_FILE)
        self.map_width = 50
        self.map_height = 50

        # Load Particle Textures
        self.particle_tex = CoreImage('{}/assets/twirl_01.png'.format(os.getcwd())).texture
        # self.add_widget(self.kivy_particle)

        ind = -1
        for name, tex in self.atlas.textures.items():

            if '_' in name:
                tile_name, tile_number = name.split('_')
            else:
                tile_name, tile_number = name, '0'

            # tex.flip_vertical()
            if self.data.get(tile_name):
                self.data[tile_name].append(tex)
            else:
                ind += 1
                self.data[tile_name] = [tex]
            self.data_size[tile_name] = tex.size

            if not self.tile_enum.get(ind):
                self.tile_enum[ind] = tile_name

        # Tree Textures
        ind = 1
        for name, tex in self.atlas_trees.textures.items():
            self.tree_data[name] = tex
            self.tree_enum[ind] = name
            ind += 1

        # Entity Textures
        for name, tex in self.char_atlas.textures.items():
            self.char_data[name] = tex

        with self.canvas.before:
            Callback(self._set_blend_func)
        with self.canvas.after:
            Callback(self._reset_blend_func)

        self.initialize_tiles()
        Window.bind(on_key_down=self._keydown)
        Window.bind(on_key_up=self._keyup)
        Clock.schedule_interval(self.check_for_keys, 60 ** -1)
        self.tile_clock = Clock.schedule_interval(self.update_tiles, 60 ** -1)

    def _set_blend_func(self, instruction):
        #glBlendFunc(self.blend_factor_source, self.blend_factor_dest)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        pass

    def _reset_blend_func(self, instruction):
        # glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        pass

    def on_player_x(self, instance, value):
        # Keep player_x between -tile_size and tile_size
        if self.player_x >= self.tile_size:
            self.viewpane_center_x -= 1
            self.player_x -= self.tile_size
        elif self.player_x <= -self.tile_size:
            self.viewpane_center_x += 1
            self.player_x += self.tile_size

        self.player.x = ((self.viewpane_center_x + 1) * self.tile_size) - self.player_x
        # self.player.x -= value

    def on_player_y(self, instance, value):
        # Keep player_x between -tile_size and tile_size
        if self.player_y >= self.tile_size:
            self.viewpane_center_y -= 1
            self.player_y -= self.tile_size

        elif self.player_y <= -self.tile_size:
            self.viewpane_center_y += 1
            self.player_y += self.tile_size

        self.player.y = ((self.viewpane_center_y + 1) * self.tile_size) - self.player_y
        # self.player.y -= value

    def toggle_player_turn(self, dt):
        self.player_turn = True

    def check_for_keys(self, dt):

        # if not self.player_turn:
        #     return

        x = self.player.x//self.tile_size
        y = self.player.y//self.tile_size

        # if self.pressed_keys[115]:
        if self.pressed_keys[115] and self.viewpane_center_y >= 0:
            # print(self.tree_map[y-1][x], not self.tree_map[y-1][x])
        # if self.pressed_keys[115] and self.viewpane_center_y > 0 + (self.height//2) // self.tile_size - 1:
            if not self.tree_map[y-1][x]:
                self.player_y += self.player_speed
                # self.player_turn = False
                # Clock.schedule_once(self.toggle_player_turn, self.player_turn_speed)

        # if self.pressed_keys[119]:
        if self.pressed_keys[119] and self.viewpane_center_y <= self.map_height - 2:
            # print(self.tree_map[y+1][x], not self.tree_map[y+1][x])
        # if self.pressed_keys[119] and self.viewpane_center_y < self.map_height - (self.height//2) // self.tile_size - 1:
            if not self.tree_map[y+1][x]:
                self.player_y -= self.player_speed
                # self.player_turn = False
                # Clock.schedule_once(self.toggle_player_turn, self.player_turn_speed)

        # if self.pressed_keys[100]:
        if self.pressed_keys[100] and self.viewpane_center_x <= self.map_width - 2:
            if not self.tree_map[y][x+1]:
                self.player_x -= self.player_speed
                # self.player_turn = False
                # Clock.schedule_once(self.toggle_player_turn, self.player_turn_speed)

        # if self.pressed_keys[97]:
        if self.pressed_keys[97] and self.viewpane_center_x >= 0:
        # if self.pressed_keys[97] and self.viewpane_center_x > 0 + (self.width//2) // self.tile_size - 1:
        #     print(self.tree_map[y][x-1], not self.tree_map[y][x-1])
            if not self.tree_map[y][x-1]:
                self.player_x += self.player_speed
                # self.player_turn = False
                # Clock.schedule_once(self.toggle_player_turn, self.player_turn_speed)

    def _keyup(self, keyboard, keycode, text, *args,**kwargs):
        pressed_key = keycode
        self.pressed_keys[pressed_key] = False

    def _keydown(self, keyboard, keycode, text, modifiers, *args, **kwargs):
        pressed_key = keycode
        self.pressed_keys[pressed_key] = True

    def reset_generation(self):
        # Map Terrain
        tile_indexes = len(self.data.keys()) - 1
        self.map = [[randint(0, tile_indexes) for i in range(self.map_width)] for j in range(self.map_height)]
        self.map_clock = [[0 for i in range(self.map_width)] for j in range(self.map_height)]

        # Create Border Around Map
        for x in range(self.map_width):
            self.map[0][x] = 0

        for y in range(self.map_height):
            self.map[y][0] = 0

        for x in range(self.map_width):
            self.map[self.map_height - 1][x] = 0

        for y in range(self.map_height):
            self.map[y][self.map_width - 1] = 0

        # Terrain 2nd Layer
        self.cellular_automata = CellularAutomata()
        self.cellular_automata.width = self.map_width
        self.cellular_automata.height = self.map_height
        self.cellular_automata.chance = 40
        self.cellular_automata.min_count = 5
        self.cellular_automata.iterations = 0
        self.cellular_automata.pillar_iterations = 1
        self.cellular_automata.flood_tries = 5
        self.cellular_automata.goal_percentage = 30  # above 30% seems to be a good target
        self.cellular_automata.generate()

        tree_indexes = len(self.tree_data.keys()) - 1
        self.tree_map = [[randint(1, tree_indexes) if self.cellular_automata.grid[j][i] == 1 else '' for i in range(self.map_width)] for j in range(self.map_height)]

        for row in reversed(self.tree_map):
            print(row)

        # Viewpane Center
        self.viewpane_center_x = randint(1, self.map_width - 2)
        self.viewpane_center_y = randint(1, self.map_height - 2)

        # Player Input Variables
        self.player = Entity(name=choice(list(self.char_data.keys())))
        self.player.x = self.viewpane_center_x * self.tile_size
        self.player.y = self.viewpane_center_y * self.tile_size
        print(self.player.x//self.tile_size, self.player.y//self.tile_size, self.tree_map[self.player.x//self.tile_size][self.player.y//self.tile_size])
        # Particles
        avg = (self.map_width + self.map_height) // 2

        # self.particles = [Particle(name='muzzle_01',
        #                            x=randint(0, self.map_width-1) * self.tile_size,
        #                            y=randint(0, self.map_height-1) * self.tile_size,
        #                            scale=1,
        #                            texture=self.particle_tex) for i in range(avg)]
        self.particles = [Particle(name='twirl_01',
                                x=randint(0, self.map_width-1) * self.tile_size,
                                y=randint(0, self.map_height-1) * self.tile_size,
                                scale=1, texture=self.particle_tex) for i in range(avg)]

        print('{} Particles generated'.format(len(self.particles)))

        # Char Entities
        char_names = list(self.char_data.keys())
        self.entities = [Entity(name=choice(char_names),
                                x=area[1] * self.tile_size,
                                y=area[0] * self.tile_size) for area in self.cellular_automata.areas_of_interest]
        self.entities.append(self.player)
        # avg = (self.map_width + self.map_height) // 2
        # self.entities = [Entity(name=choice(char_names),
        #                         x=randint(0, self.map_width-1) * self.tile_size,
        #                         y=randint(0, self.map_height-1) * self.tile_size) for i in range(avg)]

        print('{} NPCs generated'.format(len(self.entities)))

    def initialize_tiles(self):
        # Create all Texture Layers
        self.blank_tex = Texture.create(size=self.size, colorfmt='rgba')
        self.blank_tex.blit_buffer(pbuffer=b'\x00\x00\x00\xff' * self.tile_size * self.tile_size * 4, size=(self.tile_size, self.tile_size), colorfmt='rgba', bufferfmt='ubyte')
        self.fov_tex = Texture.create(size=self.size, colorfmt='rgba')
        self.fov_tex.blit_buffer(pbuffer=b'\x00\x00\x00\xff' * self.tile_size * self.tile_size * 4, size=(self.tile_size, self.tile_size), colorfmt='rgba', bufferfmt='ubyte')
        self.tex = Texture.create(size=self.size, colorfmt='rgba')
        self.tex.mag_filter = 'nearest'
        self.entities_tex = Texture.create(size=self.size, colorfmt='rgba')
        self.entities_tex.mag_filter = 'nearest'

        # Initialize Texture Data
        size = self.width * self.height * 4
        buf = [255 for _ in range(size)]
        arr = array("B", buf)
        self.tex.blit_buffer(arr, colorfmt='rgba', bufferfmt=BUFFERFMT)
        self.reset_generation()
        # self.render_canvas()

    def resize(self, new_size):
        self.size = self.width + new_size, self.height + new_size
        if self.parent:
            self.parent.size = self.width - self.tile_size, self.height - self.tile_size

        self.initialize_tiles(0)

    def update_tiles(self, dt):
        # print(self.player.x, self.player.y)
        self.canvas.clear()
        viewpane_width = (self.width // self.tile_size) // 2
        viewpane_height = (self.height // self.tile_size) // 2
        fov_dist = 6
        center = (viewpane_width + viewpane_height + 1) // 2

        # Find Entities within View Pane
        entities_to_render = {}
        entities_to_render = self.find_entities_within_fov(viewpane_width, viewpane_height, fov_dist, dt)

        # Find Particle Entities within View Pane
        particles_to_render = {}
        particles_to_render = self.find_particles_within_fov(viewpane_width, viewpane_height, fov_dist, dt)

        with self.canvas:
            Color(1, 1, 1, 1.0)

            # Render Background Tiles Within
            for y in range(self.viewpane_center_y + viewpane_height + 1, self.viewpane_center_y - viewpane_height - 1, -1):
                for x in range(self.viewpane_center_x + viewpane_width + 1, self.viewpane_center_x - viewpane_width - 1, -1):

                    Color(1, 1, 1, 1.0)
                    correct_x = x - self.viewpane_center_x + viewpane_width  # normalize to l0 thru map width
                    correct_y = y - self.viewpane_center_y + viewpane_height

                    try:
                        1 // (abs(y + 1) + y + 1)  # check for negative numbers
                        1 // (abs(x + 1) + x + 1)
                        tile_integer = self.map[y][x]
                        tile_name = self.tile_enum[(floor(tile_integer))]
                        tile_clock_ind = floor(self.map_clock[y][x])
                        tile_tex = self.data[tile_name][tile_clock_ind]

                    except ZeroDivisionError:
                        tile_tex = self.blank_tex  # default to black
                    except IndexError:
                        try:
                            self.map_clock[y][x] = 0
                            tile_tex = self.data[tile_name][0]
                        except:
                            tile_tex = self.blank_tex  # default to black
                    Color(1, 1, 1, 1.0)
                    Rectangle(texture=tile_tex,
                              size=tile_tex.size,
                              pos=((correct_x * self.tile_size) + self.parent.x + self.player_x - self.tile_size,
                                   (correct_y * self.tile_size) + self.parent.y + self.player_y - self.tile_size)
                              )

                    # Render Trees
                    try:
                        correct_x = x - self.viewpane_center_x + viewpane_width  # normalize to 0 thru map width
                        correct_y = y - self.viewpane_center_y + viewpane_height
                        1 // (abs(y + 1) + y + 1)
                        1 // (abs(x + 1) + x + 1)
                        tile_integer = self.tree_map[y][x]
                        tile_name = self.tree_enum[(floor(tile_integer))]
                        tile_tex = self.tree_data[tile_name]
                        # Color(1, 1, 1, randint(0, 255) / 255)
                        # Color(1, 1, 1, randint(200, 255) // 255)
                        Rectangle(texture=tile_tex,
                                  size=tile_tex.size,
                                  pos=((correct_x * self.tile_size) + self.parent.x + self.player_x - self.tile_size,
                                       (correct_y * self.tile_size) + self.parent.y + self.player_y - self.tile_size))
                    except TypeError:
                        # If "None" is encountered from tree_map array with no object placed
                        # continue
                        pass
                    except IndexError:
                        # If x/y coordinates exceed tree_map array
                        # continue
                        pass
                    except ZeroDivisionError:
                        # Check for any x/y coordinates dips below 0, otherwise will select from end of array
                        # continue
                        pass

                    # Render Particle
                    p = particles_to_render.get((x, y))
                    if p:
                        p.update(dt)
                        correct_x = (p.x // self.tile_size) - self.viewpane_center_x + viewpane_width
                        correct_y = (p.y // self.tile_size) - self.viewpane_center_y + viewpane_height
                        PushMatrix()
                        r = Rotate()
                        r.angle = p.angle
                        r.axis = (0, 0, 1)
                        # r = Scale()
                        # r.x = p.scale
                        # r.y = p.scale
                        r.origin = (correct_x * self.tile_size + self.parent.x + self.player_x - (self.tile_size
                                    //2)), (correct_y * self.tile_size + self.parent.y + self.player_y - (self.tile_size//2))
                        Color(1, 1, 0, 1.0)
                        Rectangle(texture=p.texture,
                                  size=p.texture.size,
                                  pos=((correct_x * self.tile_size + self.parent.x + self.player_x - self.tile_size),
                                       (correct_y * self.tile_size + self.parent.y + self.player_y - self.tile_size)))
                        PopMatrix()

                    # Render Entities
                    e = entities_to_render.get((x, y))
                    if e:
                        entity_tex = self.char_data[e.name]
                        correct_x = (e.x + self.tile_size * viewpane_width) - \
                                    (self.viewpane_center_x * self.tile_size)
                        correct_y = (e.y + self.tile_size * viewpane_height) - (
                                    self.viewpane_center_y * self.tile_size)
                        Rectangle(texture=entity_tex,
                                  size=entity_tex.size,
                                  pos=((correct_x + self.parent.x + self.player_x - self.tile_size),
                                       (correct_y + self.parent.y + self.player_y - self.tile_size)))
            # FOV Rendering
            for x in range(self.viewpane_center_x + viewpane_width+1, self.viewpane_center_x - viewpane_width - 1, -1):
                for y in range(self.viewpane_center_y + viewpane_height+1, self.viewpane_center_y - viewpane_height - 1, -1):
                    # FOV/Shadow Texture
                    correct_x = x - self.viewpane_center_x + viewpane_width  # normalize to 0 thru map width
                    correct_y = y - self.viewpane_center_y + viewpane_height

                    # Outside FOV
                    dist = self.calculate_distance(correct_x-1, correct_y-1, center, center) + 0.05
                    if  dist > fov_dist:
                        Color(0, 0, 0, 0.5)
                        Rectangle(texture=self.blank_tex,
                                  size=self.blank_tex.size,
                                  pos=((correct_x * self.tile_size) + self.parent.x + self.player_x - self.tile_size,
                                       (correct_y * self.tile_size) + self.parent.y + self.player_y - self.tile_size))
                    # else:  # Within FOV
                    #     Color(1, 1, 1, 1/dist)
                    #     Rectangle(texture=self.blank_tex,
                    #               size=self.blank_tex.size,
                    #               pos=((correct_x * self.tile_size) + self.parent.x + self.player_x - self.tile_size,
                    #                    (correct_y * self.tile_size) + self.parent.y + self.player_y - self.tile_size))

    def find_entities_within_fov(self, viewpane_width, viewpane_height, fov_dist, dt):
        # Find All Entities Within fov_dist and return in {position:entity_object} form
        # Note: does not account if more than one entity is in the same position
        center = (viewpane_width + viewpane_height + 1) // 2
        render_entities = [e for e in self.entities \
                           if self.calculate_distance(
                (e.x // self.tile_size) - self.viewpane_center_x + viewpane_width - 1,
                (e.y // self.tile_size) - self.viewpane_center_y + viewpane_height - 1, center,
                center) <= fov_dist]

        return {(e.x // self.tile_size, e.y // self.tile_size): e for e in render_entities}

    def find_particles_within_fov(self, viewpane_width, viewpane_height, fov_dist, dt):
        center = (viewpane_width + viewpane_height + 1) // 2
        render_particles = [p for p in self.particles \
                           if self.calculate_distance(
                (p.x // self.tile_size) - self.viewpane_center_x + viewpane_width - 1,
                (p.y // self.tile_size) - self.viewpane_center_y + viewpane_height - 1, center,
                center) <= fov_dist]

        return {(p.x // self.tile_size, p.y // self.tile_size): p for p in render_particles}

    @staticmethod
    def calculate_distance(x1, y1, x2, y2):
        return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


class RendererApp(App):
    def build(self):
        return AtlasLayout()


if __name__ == '__main__':
    RendererApp().run()
