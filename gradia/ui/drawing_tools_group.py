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

from gi.repository import Gtk, Adw, Gdk, Gio, GLib, Pango
from gradia.overlay.drawing_actions import DrawingMode
from gradia.overlay.drawing_overlay import DrawingOverlay

class DrawingToolsGroup(Adw.PreferencesGroup):
    def __init__(self):
        super().__init__(title=_("Annotation Tools"))

        self.fill_sensitive_modes = {DrawingMode.SQUARE, DrawingMode.CIRCLE}
        self.font_sensitive_modes = {DrawingMode.TEXT}
        self.tool_buttons = {}

        self.fonts = ["Caveat", "Adwaita Sans", "Adwaita Mono", "Noto Sans"]

        self._build_ui()

    def _build_ui(self):
        self._create_tools_row()
        self._create_stroke_color_row()
        self._create_fill_or_font_stack_row()
        self.tool_buttons[DrawingMode.PEN].set_active(True)

    def _create_tools_row(self):
        tools_row = Adw.ActionRow()
        tools_grid = Gtk.Grid(
            margin_start=6,
            margin_end=6,
            margin_top=6,
            margin_bottom=6,
            row_spacing=6,
            column_spacing=6,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER
        )

        tools_data = [
            (DrawingMode.SELECT, "pointer-primary-click-symbolic", 0, 0),
            (DrawingMode.PEN, "edit-symbolic", 1, 0),
            (DrawingMode.TEXT, "text-insert2-symbolic", 2, 0),
            (DrawingMode.LINE, "draw-line-symbolic", 3, 0),
            (DrawingMode.ARROW, "arrow1-top-right-symbolic", 4, 0),
            (DrawingMode.SQUARE, "box-small-outline-symbolic", 0, 1),
            (DrawingMode.CIRCLE, "circle-outline-thick-symbolic", 1, 1),
            (DrawingMode.HIGHLIGHTER, "marker-symbolic", 2, 1),
            (DrawingMode.CENSOR, "checkerboard-big-symbolic", 3, 1),
            (DrawingMode.NUMBER, "one-circle-symbolic", 4, 1),
        ]

        for drawing_mode, icon_name, col, row in tools_data:
            button = Gtk.ToggleButton(icon_name=icon_name)
            button.set_tooltip_text(drawing_mode.value)
            button.set_size_request(40, 40)
            button.get_style_context().add_class("flat")
            button.get_style_context().add_class("circular")
            button.connect("toggled", self._on_button_toggled, drawing_mode)

            tools_grid.attach(button, col, row, 1, 1)
            self.tool_buttons[drawing_mode] = button

        tools_row.set_child(tools_grid)
        self.add(tools_row)

    def _create_stroke_color_row(self):
        row = Adw.ActionRow(title=_("Stroke Color"))
        self.stroke_color_button = Gtk.ColorButton(valign=Gtk.Align.CENTER)
        self.stroke_color_button.set_rgba(Gdk.RGBA(1, 1, 1, 1))
        self.stroke_color_button.connect("color-set", self._on_color_set)

        row.add_suffix(self.stroke_color_button)
        self.add(row)

    def _create_fill_or_font_stack_row(self):
        self.stack_row = Adw.ActionRow()
        self.stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            transition_duration=300,
            valign=Gtk.Align.CENTER,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12
        )

        self._create_fill_color_ui()
        self._create_font_dropdown_ui()

        self.stack_row.set_child(self.stack)
        self.add(self.stack_row)

    def _create_fill_color_ui(self):
        fill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)

        reset_button = Gtk.Button(icon_name="edit-clear-symbolic")
        reset_button.get_style_context().add_class("flat")
        reset_button.set_tooltip_text(_("Reset Fill"))
        reset_button.connect("clicked", self._on_reset_fill_clicked)

        self.fill_color_button = Gtk.ColorButton(use_alpha=True)
        self.fill_color_button.set_rgba(Gdk.RGBA(0, 0, 0, 0))
        self.fill_color_button.connect("color-set", self._on_fill_color_set)

        fill_box.append(reset_button)
        fill_box.append(self.fill_color_button)

        fill_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        fill_label = Gtk.Label(label=_("Fill"), halign=Gtk.Align.START)
        fill_label.set_hexpand(True)

        fill_container.append(fill_label)
        fill_container.append(fill_box)
        fill_container.set_spacing(6)

        self.stack.add_named(fill_container, "fill")

    def _create_font_dropdown_ui(self):
        font_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)

        string_list = Gtk.StringList.new(self.fonts)
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._font_factory_setup)
        factory.connect("bind", self._font_factory_bind)

        self.font_dropdown = Gtk.DropDown()
        self.font_dropdown.set_model(string_list)
        self.font_dropdown.set_factory(factory)
        self.font_dropdown.set_selected(0)
        self.font_dropdown.set_property("width-request", 150)
        self.font_dropdown.connect("notify::selected", self._on_font_selected)

        font_box.append(self.font_dropdown)

        font_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        font_label = Gtk.Label(label=_("Font"), halign=Gtk.Align.START)
        font_label.set_hexpand(True)

        font_container.append(font_label)
        font_container.append(font_box)
        font_container.set_spacing(6)

        self.stack.add_named(font_container, "font")

    def _font_factory_setup(self, factory, list_item):
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        list_item.set_child(label)

    def _font_factory_bind(self, factory, list_item):
        label = list_item.get_child()
        string_object = list_item.get_item()
        font_name = string_object.get_string()
        label.set_text(font_name)

        attr_list = Pango.AttrList()
        font_desc = Pango.FontDescription(f"{font_name} 12")
        attr_font = Pango.attr_font_desc_new(font_desc)
        attr_list.insert(attr_font)
        label.set_attributes(attr_list)

    def _on_button_toggled(self, button: Gtk.ToggleButton, drawing_mode):
        if button.get_active():
            self._deactivate_other_tools(drawing_mode)
            self._update_stack_for_mode(drawing_mode)
            self._activate_draw_mode_action(drawing_mode)
        else:
            self._ensure_one_tool_active(button, drawing_mode)

    def _deactivate_other_tools(self, current_mode):
        for mode, btn in self.tool_buttons.items():
            if mode != current_mode and btn.get_active():
                btn.set_active(False)

    def _update_stack_for_mode(self, drawing_mode):
        if drawing_mode in self.fill_sensitive_modes:
            self.stack_row.set_sensitive(True)
            self.stack.set_visible_child_name("fill")
        elif drawing_mode in self.font_sensitive_modes:
            self.stack_row.set_sensitive(True)
            self.stack.set_visible_child_name("font")
        else:
            self.stack_row.set_sensitive(False)

    def _activate_draw_mode_action(self, drawing_mode):
        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action("draw-mode")
            if action:
                action.activate(GLib.Variant('s', drawing_mode.value))

    def _ensure_one_tool_active(self, button, drawing_mode):
        any_active = any(
            btn.get_active() for mode, btn in self.tool_buttons.items() if mode != drawing_mode
        )
        if not any_active:
            button.set_active(True)

    def _on_reset_fill_clicked(self, _btn):
        self.fill_color_button.set_rgba(Gdk.RGBA(0, 0, 0, 0))
        self.fill_color_button.emit("color-set")

    def _on_color_set(self, color_btn: Gtk.ColorButton):
        rgba = color_btn.get_rgba()
        self._activate_color_action("pen-color", rgba)

    def _on_fill_color_set(self, color_btn: Gtk.ColorButton):
        rgba = color_btn.get_rgba()
        self._activate_color_action("fill-color", rgba)

    def _on_font_selected(self, dropdown: Gtk.DropDown, _param):
        selected_index = dropdown.get_selected()
        if 0 <= selected_index < len(self.fonts):
            font_name = self.fonts[selected_index]
            app = Gio.Application.get_default()
            if app:
                action = app.lookup_action("font")
                if action:
                    action.activate(GLib.Variant('s', font_name))

    def _activate_color_action(self, action_name: str, rgba: Gdk.RGBA):
        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action(action_name)
            if action:
                color_str = f"{rgba.red:.3f},{rgba.green:.3f},{rgba.blue:.3f},{rgba.alpha:.3f}"
                action.activate(GLib.Variant('s', color_str))
