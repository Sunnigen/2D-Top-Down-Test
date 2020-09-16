Simulate 2D Top Down RPG using Kivy Textures

Kivy 1.11.1
Python 3.7.7


*** UPDATE 09152020 ***

I underestimated the power of the "Rectangle" class. It is pretty powerful in leveraging various drawing instructions. After tinkering for (2) weeks. The textures no longer overwrite each other. See below for the output. There are (2) main issues below:

1. Moving around the "player" character reveals a disjointed tile sensor when moving around.
2. There are times the "player" character will render "on top" of the tree instead of behind. This is due to the fact that tiles are rendered from bottom to top, right to left(?). So any texture to the left of another would overrwrite?

![alt-text](https://github.com/Sunnigen/2D-Top-Down-Test/blob/master/progress-09152020.gif)

***********************


Will work if git clone'd and main.py is executed.

How do I blit data onto an existing texture keeping the rgba values that already exist and overlaying new bytecode without overwriting. Note the tree image's white areas are transparent.

GOAL: Trees that "blend" into each other

![alt-text](https://github.com/Sunnigen/2D-Top-Down-Test/blob/master/trees_example.png)

ISSUE: Trees are overwriting each other, although their white space is transparent
![alt-text](https://github.com/Sunnigen/2D-Top-Down-Test/blob/master/overwriting_tex_example.gif)



