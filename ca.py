from random import randint
from collections import deque


class CellularAutomata:
    width = 20
    height = 20
    grid = None
    chance = 40  # percentage chance of randomly generating wall
    min_count = 5  # min count of surrounding walls for the automata rules
    iterations = 0
    pillar_iterations = 1
    flood_tries = 5
    goal_percentage = 30
    open_percentage = 0
    areas_of_interest = []  # areas of open space

    def generate(self):
        self.reset_grid()

        # Randomly populated grid
        self.populate_grid()

        # Iterate Cellular Automata Rules
        for i in range(self.pillar_iterations):
            print("{0} iteration(s) of automata with pillars:".format(i + 1))
            self.automata_iteration(make_pillars=1)

        # Iterate Modified Cellular Automata Rules to Add Walls
        for i in range(self.iterations):
            print("{0} iteration(s) of regular automata:".format(i + 1))
            self.automata_iteration(make_pillars=0)

        # print("\nAfter flood algorithm to find the biggest cave:")
        self.flood_find_empty()
        self.find_areas_if_interest()
        """
        - self reminder to try checking map size 
        - https://stackoverflow.com/questions/1331471/in-memory-size-of-a-python-structure
        """

    def print_grid(self, wall_char, empty_char, other_car='$ ', grid=None):
        final_str = ""
        final_str += "\n"

        if grid:
            _grid = grid
        else:
            _grid = self.grid

        for i in range(len(_grid[0])):
            for j in range(len(_grid)):
                if _grid[j][i] == 1:
                    final_str += wall_char
                elif _grid[j][i] == 0:
                    final_str += empty_char
                else:
                    final_str += other_car
            final_str += "\n"
        final_str += "\n"
        print(final_str)

    def reset_grid(self):
        new_grid = [[0 for x in range(self.height)] for y in range(self.width)]
        for i in range(len(new_grid)):
            for j in range(len(new_grid[i])):
                if i == 0 or j == 0 or i == len(new_grid) - 1 or j == len(new_grid[0]) - 1:
                    new_grid[i][j] = 1
        self.grid = new_grid

    def populate_grid(self):
        for i in range(len(self.grid)):  # reminder to test with: for index, value in enumerate(grid)
            for j in range(len(self.grid[0])):
                if randint(0, 100) <= self.chance:  # test with list comprehension instead??
                    self.grid[i][j] = 1

    def automata_iteration(self, make_pillars):
        make_grid = [row[:] for row in self.grid]
        for i in range(1, len(self.grid) - 1):
            for j in range(1, len(self.grid[0]) - 1):
                count = 0

                # Check 4x4 area around cell and count obstacles
                for k in range(-1, 2):
                    for l in range(-1, 2):
                        if self.grid[i + k][j + l] == 1:
                            count += 1

                # Add Wall or Remove Wall
                if count >= self.min_count or (count == 0 and make_pillars == 1):
                    make_grid[i][j] = 1
                else:
                    make_grid[i][j] = 0
        self.grid = make_grid

    @staticmethod
    def inside_circle(center_x, center_y, point_x, point_y, radius):
        dx = center_x - point_x
        dy = center_y - point_y
        distance_squared = dx * dx + dy * dy
        return distance_squared <= radius * radius

    def find_areas_if_interest(self, radius=1):
        # Find Areas of Interest to Spawn Prefabs or entities
        possible_areas = []

        for center_x in range(self.width):
            for center_y in range(self.height):

                open_area_count = 0
                # Cache Circle Dimensions
                top = max(0, center_y - radius)
                bottom = min(self.height, center_y + radius)
                left = max(0, center_x - radius)
                right = min(self.width, center_x + radius)

                # Iterate Through Circle Bounding Box
                for point_x in range(left, right):
                    for point_y in range(top, bottom):
                        # print(x, y)

                        if self.grid[point_x][point_y] != 1 and (point_x, point_y) not in possible_areas:
                            open_area_count += 1
                # print('open_area_count:', open_area_count)
                if open_area_count >= 4:
                    possible_areas.append((center_x, center_y))

        # Among All Possible Areas, Remove Close Areas
        encounter_spread_factor = randint(3, 6)  # spread out factor
        radius = min(self.width // encounter_spread_factor, self.height // encounter_spread_factor)
        areas = []
        while possible_areas:
            center_x, center_y = possible_areas.pop()
            # Cache Circle Dimensions
            top = max(0, center_y - radius)
            bottom = min(self.height, center_y + radius)
            left = max(0, center_x - radius)
            right = min(self.width, center_x + radius)

            for x in range(left, right):
                for y in range(top, bottom):
                    if self.inside_circle(center_x, center_y, x, y, radius) and (x, y) in possible_areas and \
                            (x, y) != (center_x, center_y):
                        possible_areas.remove((x, y))
            areas.append((center_x, center_y))
        self.areas_of_interest = areas

    def flood_find_empty(self):
        times_remade = 0
        percentage = 0
        make_grid = [[1 for x in range(len(self.grid[0]))] for y in range(len(self.grid))]
        while times_remade < self.flood_tries and percentage < self.goal_percentage:
            copy_grid = [row[:] for row in self.grid]
            open_count = 0
            times_remade += 1
            unvisited = deque([])
            make_grid = [[1 for x in range(len(self.grid[0]))] for y in range(len(self.grid))]
            # find a random empty space, hope it's the biggest cave
            randx = randint(0, len(self.grid) - 1)
            randy = randint(0, len(self.grid[0]) - 1)
            while self.grid[randx][randy] == 1:
                randx = randint(0, len(self.grid) - 1)
                randy = randint(0, len(self.grid[0]) - 1)
            unvisited.append([randx, randy])
            while len(unvisited) > 0:
                current = unvisited.popleft()
                make_grid[current[0]][current[1]] = 0
                for k in range(-1, 2):
                    for l in range(-1, 2):
                        if current[0] + k >= 0 and current[0] + k < len(self.grid) and current[1] + l >= 0 and current[
                            1] + l < len(self.grid[0]):  # if we're not out of bounds
                            if copy_grid[current[0] + k][current[1] + l] == 0:  # if it's an empty space
                                copy_grid[current[0] + k][current[1] + l] = 2  # mark visited
                                open_count += 1
                                unvisited.append([current[0] + k, current[1] + l])
            percentage = open_count * 100 / (len(self.grid) * len(self.grid[0]))
            # print("counted {0}, {1}%...".format(open_count, percentage))
        self.grid = make_grid
        self.open_percentage = percentage

        # if percentage < self.goal_percentage:
        #     print("Failed to produce a big enough cave after {0} tries...".format(self.flood_tries))
        # else:
        #     print("Percentage of open space: {0}%".format(percentage))


if __name__ == "__main__":
    c = CellularAutomata()
    c.width = 50
    c.height = 50
    c.chance = 40
    c.min_count = 5
    c.iterations = 0
    c.pillar_iterations = 1
    c.flood_tries = 5
    c.goal_percentage = 30  # above 30% seems to be a good target
    c.generate()
    for row in c.grid:
        print(row)

    # c.print_grid('# ', '· ')

    for x in range(c.width):
        for y in range(c.height):
            if (x, y) in c.areas_of_interest:
                c.grid[x][y] = 3

    c.print_grid('# ', '· ', '$ ')
