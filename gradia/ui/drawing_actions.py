# Copyright (C) 2025 Alexander Vanhee
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk, Gdk, Gio, cairo, Pango, PangoCairo
from enum import Enum
import math
from gradia.backend.logger import Logger

logging = Logger()

class DrawingMode(Enum):
    PEN = _("Pen")
    ARROW = _("Arrow")
    LINE = _("Line")
    SQUARE = _("Square")
    CIRCLE = _("Circle")
    TEXT = _("Text")
    SELECT = _("Select")
    HIGHLIGHTER = _("Highlighter")
    CENSOR = _("Censor")
    NUMBER = _("Number")

class DrawingAction:
    DEFAULT_PADDING = 0.02

    def draw(self, cr: cairo.Context, image_to_widget_coords, scale: float):
        raise NotImplementedError

    def get_bounds(self):
        raise NotImplementedError

    def apply_padding(self, bounds, extra_padding=0.0):
        min_x, min_y, max_x, max_y = bounds
        padding = self.DEFAULT_PADDING + extra_padding
        return (min_x - padding, min_y - padding, max_x + padding, max_y + padding)

    def contains_point(self, x, y):
        min_x, min_y, max_x, max_y = self.get_bounds()
        if isinstance(self, (LineAction, ArrowAction)):
            px, py = x, y
            x1, y1 = self.start
            x2, y2 = self.end
            line_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
            if line_len_sq == 0:
                return math.hypot(px - x1, py - y1) < self.DEFAULT_PADDING
            t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_len_sq
            t = max(0, min(1, t))
            closest_x = x1 + t * (x2 - x1)
            closest_y = y1 + t * (y2 - y1)
            dist_sq = (px - closest_x)**2 + (py - closest_y)**2
            return dist_sq < (0.01 + self.width / 200.0)**2
        return min_x <= x <= max_x and min_y <= y <= max_y

    def translate(self, dx, dy):
        raise NotImplementedError

class StrokeAction(DrawingAction):
    def __init__(self, stroke, color, pen_size):
        self.stroke = stroke
        self.color = color
        self.pen_size = pen_size

    def draw(self, cr, image_to_widget_coords, scale):
        if len(self.stroke) < 2:
            return
        coords = [image_to_widget_coords(x, y) for x, y in self.stroke]
        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.pen_size * scale)
        cr.move_to(*coords[0])
        for point in coords[1:]:
            cr.line_to(*point)
        cr.stroke()

    def get_bounds(self):
        if not self.stroke:
            return (0, 0, 0, 0)
        xs, ys = zip(*self.stroke)
        return self.apply_padding((min(xs), min(ys), max(xs), max(ys)))

    def translate(self, dx, dy):
        self.stroke = [(x + dx, y + dy) for x, y in self.stroke]

class ArrowAction(DrawingAction):
    def __init__(self, start, end, color, arrow_head_size, width):
        self.start = start
        self.end = end
        self.color = color
        self.arrow_head_size = arrow_head_size
        self.width = width

    def draw(self, cr, image_to_widget_coords, scale):
        start_x, start_y = image_to_widget_coords(*self.start)
        end_x, end_y = image_to_widget_coords(*self.end)
        distance = math.hypot(end_x - start_x, end_y - start_y)
        if distance < 2:
            return
        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.width * scale)
        cr.move_to(start_x, start_y)
        cr.line_to(end_x, end_y)
        cr.stroke()
        angle = math.atan2(end_y - start_y, end_x - start_x)
        head_len = min(self.arrow_head_size * scale, distance * 0.3)
        head_angle = math.pi / 6
        x1 = end_x - head_len * math.cos(angle - head_angle)
        y1 = end_y - head_len * math.sin(angle - head_angle)
        x2 = end_x - head_len * math.cos(angle + head_angle)
        y2 = end_y - head_len * math.sin(angle + head_angle)
        cr.move_to(end_x, end_y)
        cr.line_to(x1, y1)
        cr.move_to(end_x, end_y)
        cr.line_to(x2, y2)
        cr.stroke()

    def get_bounds(self):
        min_x = min(self.start[0], self.end[0])
        max_x = max(self.start[0], self.end[0])
        min_y = min(self.start[1], self.end[1])
        max_y = max(self.start[1], self.end[1])
        return self.apply_padding((min_x, min_y, max_x, max_y))

    def translate(self, dx, dy):
        self.start = (self.start[0] + dx, self.start[1] + dy)
        self.end = (self.end[0] + dx, self.end[1] + dy)

class TextAction(DrawingAction):
    def __init__(self, position, text, color, font_size,image_bounds, font_family="Sans"):
        self.position = position
        self.text = text
        self.color = color
        self.font_size = font_size
        self.font_family = font_family
        self.image_bounds = image_bounds

    def draw(self, cr, image_to_widget_coords, scale):
        if not self.text.strip():
            return
        x, y = image_to_widget_coords(*self.position)
        cr.set_source_rgba(*self.color)
        layout = PangoCairo.create_layout(cr)
        font_desc = Pango.FontDescription()
        font_desc.set_family(self.font_family)
        font_desc.set_size(int(self.font_size * scale * Pango.SCALE))
        layout.set_font_description(font_desc)
        layout.set_text(self.text, -1)
        _, logical_rect = layout.get_extents()
        text_width = logical_rect.width / Pango.SCALE
        text_height = logical_rect.height / Pango.SCALE
        cr.move_to(x - text_width / 2, y - text_height)
        PangoCairo.show_layout(cr, layout)

    def get_bounds(self):
        if not self.text.strip():
            x, y = self.position
            return (x, y, x, y)

        # Create a temporary surface and context to measure text
        import cairo
        temp_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
        temp_cr = cairo.Context(temp_surface)

        layout = PangoCairo.create_layout(temp_cr)
        font_desc = Pango.FontDescription()
        font_desc.set_family(self.font_family)
        font_desc.set_size(int(self.font_size * Pango.SCALE))
        layout.set_font_description(font_desc)
        layout.set_text(self.text, -1)

        _, logical_rect = layout.get_extents()
        text_width_px = logical_rect.width / Pango.SCALE
        text_height_px = logical_rect.height / Pango.SCALE

        reference_width = self.image_bounds[0]
        reference_height = self.image_bounds[1]
        logging.info(self.image_bounds)
        text_width = text_width_px / reference_width
        text_height = text_height_px / reference_height

        x, y = self.position
        left = x - text_width / 2
        right = x + text_width / 2
        top = y - text_height
        bottom = y

        return self.apply_padding((left, top, right, bottom))

    def translate(self, dx, dy):
        self.position = (self.position[0] + dx, self.position[1] + dy)


class LineAction(ArrowAction):
    def draw(self, cr, image_to_widget_coords, scale):
        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.width * scale)
        cr.move_to(*image_to_widget_coords(*self.start))
        cr.line_to(*image_to_widget_coords(*self.end))
        cr.stroke()

class RectAction(DrawingAction):
    def __init__(self, start, end, color, width, fill_color=None):
        self.start = start
        self.end = end
        self.color = color
        self.width = width
        self.fill_color = fill_color

    def draw(self, cr, image_to_widget_coords, scale):
        x1, y1 = image_to_widget_coords(*self.start)
        x2, y2 = image_to_widget_coords(*self.end)
        x, y = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1), abs(y2 - y1)
        if self.fill_color:
            cr.set_source_rgba(*self.fill_color)
            cr.rectangle(x, y, w, h)
            cr.fill()
        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.width * scale)
        cr.rectangle(x, y, w, h)
        cr.stroke()

    def get_bounds(self):
        min_x = min(self.start[0], self.end[0])
        max_x = max(self.start[0], self.end[0])
        min_y = min(self.start[1], self.end[1])
        max_y = max(self.start[1], self.end[1])
        return self.apply_padding((min_x, min_y, max_x, max_y))

    def translate(self, dx, dy):
        self.start = (self.start[0] + dx, self.start[1] + dy)
        self.end = (self.end[0] + dx, self.end[1] + dy)

class CircleAction(RectAction):
    def draw(self, cr, image_to_widget_coords, scale):
        x1, y1 = image_to_widget_coords(*self.start)
        x2, y2 = image_to_widget_coords(*self.end)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        rx, ry = abs(x2 - x1) / 2, abs(y2 - y1) / 2
        if rx < 1e-3 or ry < 1e-3:
            return
        cr.save()
        cr.translate(cx, cy)
        cr.scale(rx, ry)
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.restore()
        if self.fill_color:
            cr.set_source_rgba(*self.fill_color)
            cr.fill_preserve()
        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.width * scale)
        cr.stroke()

class HighlighterAction(StrokeAction):
    def draw(self, cr, image_to_widget_coords, scale):
        if len(self.stroke) < 2:
            return
        coords = [image_to_widget_coords(x, y) for x, y in self.stroke]
        cr.set_operator(cairo.Operator.MULTIPLY)
        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.pen_size * scale)
        cr.set_line_cap(cairo.LineCap.BUTT)
        cr.move_to(*coords[0])
        for point in coords[1:]:
            cr.line_to(*point)
        cr.stroke()
        cr.set_operator(cairo.Operator.OVER)
        cr.set_line_cap(cairo.LineCap.ROUND)

