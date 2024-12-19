# Basic arcade program using objects
# Displays a white window with a blue circle in the middle

# Imports
import arcade
import random
import physics_engine as pe

# import arcade.gui

# Constants
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 760
SCREEN_TITLE = "Justin & Jamie"

CHARACTER_SCALING = 0.75
BLOCK_SCALING = 0.375
LIFE_ICON_SCALING = 0.375

PLAYER_WIDTH = 96 * CHARACTER_SCALING
PLAYER_HEIGHT = 128 * CHARACTER_SCALING
BLOCK_WIDTH = 128 * BLOCK_SCALING
BLOCK_HEIGHT = 74 * BLOCK_SCALING

PLATFORM_DISTANCE = PLAYER_HEIGHT + BLOCK_HEIGHT
GAME_SPEED_UP_FACTOR = 2
GAME_MAX_BASE_SPEED = -5
GROUND_SPAWN_MULTIPLIER = 2

GRAVITY = 1
MARGIN = 32

PLAYER_SPRITE_LIST = "Player"
BLOCK_SPRITE_LIST = "Walls"
LIFE_SPRITE_LIST = "Lives"
PLAYER_SPRITE_SRC = ":resources:images/animated_characters/"
BLOCK_SPRITE_SRC = ":resources:images/tiles/"


# Classes
class BlockSprite(arcade.Sprite):
    """Base class for all flying sprites
    Flying sprites include enemies and clouds
    """

    def update(self):
        """Update the position of the sprite
        When it moves off screen to the left, remove it
        """

        # Move the sprite
        # super().update() # Don't need to bc the physics engine does this

        # Remove us if we're off screen
        if self.right < 0:
            del self


class PlayerSprite(arcade.Sprite):
    """Player sprite"""

    def __init__(self, filename, scaling, player_ind):
        super().__init__(filename=filename, scale=scaling)

        self.player_ind = player_ind
        self.starting_lives = 5
        self.remaining_lives = self.starting_lives

    def update(self):
        """Update the position of the sprite"""

        # Move the sprite
        # super().update() # Don't need to bc the physics engine does this

    def check_off_screen(self) -> tuple[int, int]:
        if self.remaining_lives <= 0:
            return (0, 0)
        # Remove us if we're off screen
        if self.right < 0 or self.top < 0 or self.left > SCREEN_WIDTH:
            (remaining, damage) = self.damage(1)
            if remaining > 0:
                self.respawn()
            return (remaining, damage)
        return (self.remaining_lives, 0)

    def damage(self, amount: int) -> tuple[int, int]:
        """Damage the player"""
        self.remaining_lives = max(self.remaining_lives - amount, 0)
        return (self.remaining_lives, amount)

    def respawn(self) -> None:
        """Respawn the player"""

        self.bottom = SCREEN_HEIGHT
        self.center_x = SCREEN_WIDTH // 2
        self.change_y = 0

    # def kill(self) -> None:
    #     """Kill the player"""
    #     del self


class InstructionView(arcade.View):
    def __init__(self) -> None:
        """Initialize the window"""

        # Call the parent class constructor
        super().__init__()
        self.button_xs = [self.window.width // 2 + x for x in [-400, -100, 200]]
        self.button_y = self.window.height // 2 - 50
        self.button_w = 200
        self.button_h = 100
        self.button_texts = ["1 player", "2 players", "3 players"]

    def on_show_view(self):
        """This is run once when we switch to this view"""
        arcade.set_background_color(arcade.color.WOOD_BROWN)

        # Reset the viewport, necessary if we have a scrolling game and we need
        # to reset the viewport back to the start so we can see what we draw.
        arcade.set_viewport(0, self.window.width, 0, self.window.height)

    def on_draw(self):
        """Draw this view"""
        self.clear()
        arcade.draw_text(
            "Choose # of Players",
            self.window.width / 2,
            self.window.height * 0.75,
            arcade.color.WHITE,
            font_size=50,
            anchor_x="center",
        )
        arcade.draw_text(
            "Player 1: Arrow keys\nPlayer 2: WASD\nPlayer 3: IJKL",
            self.window.width / 2,
            self.window.height / 2 - 150,
            arcade.color.WHITE,
            font_size=20,
            anchor_x="center",
            align="center",
            multiline=True,
            width=500,
        )

        for i in range(3):
            self.draw_button(
                self.button_xs[i],
                self.button_y,
                self.button_w,
                self.button_h,
                self.button_texts[i],
            )

    def on_mouse_press(self, _x, _y, _button, _modifiers):
        """If the user presses the mouse button, start the game."""
        if self.button_y < _y < self.button_y + self.button_h:
            for i in range(3):
                if self.button_xs[i] < _x < self.button_xs[i] + self.button_w:
                    self.start_game(i + 1)
                    return

    def on_key_press(self, key: int, modifiers: int) -> None:
        """Called whenever a key is pressed."""

        if key == arcade.key.Q:
            # Quit immediately
            arcade.close_window()

    def draw_button(self, x, y, w, h, text):
        arcade.draw_xywh_rectangle_filled(x, y, w, h, arcade.color.NAVY_BLUE)
        arcade.draw_text(
            start_x=x,
            start_y=y + (h / 2) - 10,
            width=w,
            text=text,
            align="center",
            bold=True,
            font_size=24,
        )

    def start_game(self, num_players: int) -> None:
        game_view = GameView()
        game_view.set_num_of_players(num_players)
        game_view.setup()
        self.window.show_view(game_view)


class GameView(arcade.View):
    """Our main welcome window"""

    def __init__(self) -> None:
        """Initialize the window"""

        # Call the parent class constructor
        super().__init__()

        # Set the background window
        arcade.set_background_color(arcade.color.CORNFLOWER_BLUE)  # WOOD_BROWN

        self.scene = None
        self.physics_engine = None
        self.num_of_players = 3
        self.schedules = []

        self.player_keys = [
            [arcade.key.UP, arcade.key.LEFT, arcade.key.DOWN, arcade.key.RIGHT],
            [arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D],
            [arcade.key.I, arcade.key.J, arcade.key.K, arcade.key.L],
        ]
        self.player_img_srcs = [
            "zombie/zombie_idle.png",
            "female_person/femalePerson_idle.png",
            "robot/robot_idle.png",
        ]

        self.window.set_mouse_visible(False)

    def setup(self) -> None:
        """Set up the game here. Call this function to restart the game."""

        self.platform_spawn_rate = 0.8  # Number of seconds between platform spawns
        self.platform_max_size = 5
        self.platform_min_size = 3
        self.game_movement_speed = -5
        self.player_movement_speed = 12
        self.player_jump_speed = 23
        self.game_sped_up = False
        self.distance_counter = 0
        self.is_paused = False

        self.scene = arcade.Scene()
        self.scene.add_sprite_list(PLAYER_SPRITE_LIST)
        self.scene.add_sprite_list(BLOCK_SPRITE_LIST, use_spatial_hash=True)
        self.scene.add_sprite_list(LIFE_SPRITE_LIST, use_spatial_hash=True)

        # Set up the players
        for i in range(self.num_of_players):
            player = PlayerSprite(
                PLAYER_SPRITE_SRC + self.player_img_srcs[i],
                CHARACTER_SCALING,
                player_ind=i,
            )
            player.right = 128 * (i + 1) + self.window.width // 4
            player.bottom = BLOCK_HEIGHT
            player.change_x = self.game_movement_speed
            self.scene.add_sprite(PLAYER_SPRITE_LIST, player)

            for j in range(player.starting_lives):
                life_icon = arcade.Sprite(
                    PLAYER_SPRITE_SRC + self.player_img_srcs[i], LIFE_ICON_SCALING
                )
                life_icon.left = MARGIN * (j + 1)
                life_icon.top = self.window.height - BLOCK_HEIGHT - MARGIN * (i + 1) * 2
                self.scene.add_sprite(LIFE_SPRITE_LIST, life_icon)

        # Create the ground
        self.add_platform(
            0, psize=(self.window.width * 1.5) // BLOCK_WIDTH, pleft=0, pbottom=0
        )

        # Create the 'physics engine'
        self.physics_engine = [
            arcade.PhysicsEnginePlatformer(
                self.scene[PLAYER_SPRITE_LIST][i],
                gravity_constant=GRAVITY,
                platforms=self.scene[BLOCK_SPRITE_LIST],
            )
            for i in range(self.num_of_players)
        ]

        # Spawn a new platform every second
        self.add_schedule(self.add_platform, self.platform_spawn_rate)
        self.add_schedule(
            self.add_random_floor, self.platform_spawn_rate * GROUND_SPAWN_MULTIPLIER
        )

        # Initial speed up
        # arcade.schedule(self.initial_speed_up, 1)
        # Had to comment this out because platforms were created with an initial speed based on current game speed, and weren't speeding up with the game

    def set_num_of_players(self, num_of_players: int) -> None:
        """Set the number of players"""
        self.num_of_players = num_of_players

    def on_draw(self) -> None:
        """Called whenever we need to draw our window"""

        # Clear the screen to the background color
        self.clear()

        # Draw our sprites
        self.scene.draw()

        arcade.draw_text(
            text=f"{(self.distance_counter / BLOCK_WIDTH):.2f}",
            start_x=MARGIN,
            start_y=self.window.height - BLOCK_HEIGHT - MARGIN,
            color=arcade.color.WHITE,
            font_size=30,
        )

    def on_key_press(self, key: int, modifiers: int) -> None:
        """Called whenever a key is pressed."""

        if key == arcade.key.Q:
            # Quit immediately
            arcade.close_window()

        if key == arcade.key.R:
            # Restart the game
            self.reset()

        if key == arcade.key.SPACE or key == arcade.key.P:
            self.is_paused = not self.is_paused
            self.unschedule_all() if self.is_paused else self.reschedule_all()
            # if self.is_paused:
            #     print(f"num platforms: {len(self.scene[BLOCK_SPRITE_LIST])}")

        for i in range(self.num_of_players):
            self.check_player_movement(key, i)

    def on_key_release(self, key: int, modifiers: int) -> None:
        """Called when the user releases a key."""

        for i in range(self.num_of_players):
            self.check_player_stopped(key, i)

    def on_update(self, delta_time: float) -> None:
        """Movement and game logic"""

        if self.is_paused:
            return

        for sprite_list in self.scene.sprite_lists:
            for sprite in sprite_list:
                if sprite.right < 0 or sprite.top < 0:
                    sprite = None

        for player in self.scene[PLAYER_SPRITE_LIST]:
            if player.left > self.window.width * 0.75:
                self.game_sped_up = True

        if self.game_sped_up:
            for sprite in [
                *self.scene[PLAYER_SPRITE_LIST],
                *self.scene[BLOCK_SPRITE_LIST],
            ]:
                sprite.center_x = (
                    sprite.center_x + self.game_movement_speed * GAME_SPEED_UP_FACTOR
                )
        self.distance_counter -= self.game_movement_speed * (
            1 + (self.game_sped_up * GAME_SPEED_UP_FACTOR)
        )
        self.game_sped_up = False

        # Move the player with the physics engine
        for pe in self.physics_engine:
            pe.update()

        # Damage & deletion checks
        for player in self.scene[PLAYER_SPRITE_LIST]:
            remaining, dealt = player.check_off_screen()
            # print(remaining, dealt)
            if (remaining, dealt) == (0, 0):
                # player.kill()
                continue
            if dealt:
                for i in range(dealt):
                    ind = (player.starting_lives * player.player_ind) + remaining + i
                    self.scene[LIFE_SPRITE_LIST][ind].right = 0
        for block in self.scene[BLOCK_SPRITE_LIST]:
            block.update()

    def add_platform(
        self,
        delta_time: float,
        psize: int = None,
        pleft: int = None,
        pbottom: int = None,
    ) -> None:
        """Adds a new block to the screen

        Arguments:
            delta_time {float} -- How much time has passed since the last call
        """

        platform_size = int(
            random.randint(self.platform_min_size, self.platform_max_size)
            if psize is None or psize < 0
            else psize
        )

        platform_left = int(
            (self.window.width + random.randint(0, 10)) if pleft is None else pleft
        )

        levels = (self.window.height - (BLOCK_HEIGHT * 5)) // PLATFORM_DISTANCE
        platform_bottom = int(
            random.randint(1, levels) * PLATFORM_DISTANCE
            if pbottom is None
            else pbottom
        )

        for i in range(platform_size):

            if platform_size == 1:
                block_name = BLOCK_SPRITE_SRC + "stoneHalf.png"
            elif i == 0:
                block_name = BLOCK_SPRITE_SRC + "stoneHalf_left.png"
            elif i == platform_size - 1:
                block_name = BLOCK_SPRITE_SRC + "stoneHalf_right.png"
            else:
                block_name = BLOCK_SPRITE_SRC + "stoneHalf_mid.png"

            # First, create the new block sprite
            block = BlockSprite(block_name, BLOCK_SCALING)

            # Set its position to a random height and off screen right
            block.left = platform_left + i * BLOCK_WIDTH
            block.bottom = platform_bottom

            # Set its speed to a random speed heading left
            block.change_x = self.game_movement_speed / self.num_of_players

            # Add it to the enemies list
            self.scene.add_sprite(BLOCK_SPRITE_LIST, block)

    def add_random_floor(self, delta_time: float) -> None:
        """Adds a new floor to the screen"""

        self.add_platform(delta_time, pbottom=0)

    def reset(self) -> None:
        """Reset the game"""

        # Remove all sprites
        self.scene.sprite_lists.clear()
        self.delete_schedules()
        self.setup()

    def check_player_movement(self, key: int, player_num: int) -> None:
        """Check the player movement"""

        if key == self.player_keys[player_num][0]:
            if self.physics_engine[player_num].can_jump():
                self.scene[PLAYER_SPRITE_LIST][
                    player_num
                ].change_y = self.player_jump_speed
        elif key == self.player_keys[player_num][1]:
            self.scene[PLAYER_SPRITE_LIST][player_num].change_x = (
                -self.player_movement_speed + self.game_movement_speed
            )
        elif key == self.player_keys[player_num][3]:
            self.scene[PLAYER_SPRITE_LIST][player_num].change_x = (
                self.player_movement_speed + self.game_movement_speed
            )

    def check_player_stopped(self, key: int, player_num: int) -> None:
        if key == self.player_keys[player_num][1]:
            self.scene[PLAYER_SPRITE_LIST][
                player_num
            ].change_x = self.game_movement_speed
        elif key == self.player_keys[player_num][3]:
            self.scene[PLAYER_SPRITE_LIST][
                player_num
            ].change_x = self.game_movement_speed

    def unschedule_all(self, funcs: list[list] = None) -> None:
        if funcs == None:
            funcs = self.schedules
        for func in funcs:
            arcade.unschedule(func[0])

    def add_schedule(self, func, rate: float) -> None:
        arcade.schedule(func, rate)
        self.schedules.append([func, rate])

    def reschedule_all(self, funcs: list[list] = None) -> None:
        if funcs == None:
            funcs = self.schedules
        for func in funcs:
            arcade.schedule(func[0], func[1])

    def delete_schedules(self, funcs: list[list] = None) -> None:
        if funcs == None:
            funcs = self.schedules
        for func in funcs:
            arcade.unschedule(func[0])
        self.schedules = []

    def initial_speed_up(self, delta_time: float) -> None:
        if self.game_movement_speed > GAME_MAX_BASE_SPEED:
            self.game_movement_speed -= 1


# Main code entry point
if __name__ == "__main__":

    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    start_view = InstructionView()
    window.show_view(start_view)
    # start_view.setup()

    arcade.run()


# class MyView(arcade.View):
#     def __init__(self, window: arcade.Window) -> None:
#         super().__init__(window=window)
#         self.manager = arcade.gui.UIManager()
#         self.manager.enable()

#         # Create the UITextArea
#         self.distance_text = arcade.gui.UITextArea(
#             x=64,
#             y=SCREEN_HEIGHT - 104,
#             width=400,
#             height=40,
#             text="0.00",
#             font_name=("Arial",),
#             font_size=12,
#             text_color=(255, 255, 255, 255),
#             multiline=True,
#         )

#         # Create the layout and add the text area
#         self.v_box = arcade.gui.UIBoxLayout()
#         self.v_box.add(self.distance_text.with_space_around(bottom=20))

#         # Add the layout to the manager
#         self.manager.add(
#             arcade.gui.UIAnchorWidget(
#                 anchor_x="center_x", anchor_y="center_y", child=self.v_box
#             )
#         )

#     def on_draw(self):
#         arcade.start_render()
#         self.manager.draw()
