import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Adw, Gdk, GLib

def create_header_bar(save_btn_ref, on_open_clicked, on_about_clicked, on_save_clicked, on_copy_from_clicked, on_copy_to_clicked):
    header_bar = Adw.HeaderBar()

    # Open button
    open_icon = Gtk.Image.new_from_icon_name("document-open-symbolic")
    open_btn = Gtk.Button()
    open_btn.set_child(open_icon)
    open_btn.get_style_context().add_class("flat")
    open_btn.set_tooltip_text("Open Image")
    open_btn.connect("clicked", on_open_clicked)
    header_bar.pack_start(open_btn)

    # Copy from clipboard button (on the left side)
    copy_icon = Gtk.Image.new_from_icon_name("edit-copy-symbolic")
    copy_btn = Gtk.Button()
    copy_btn.set_child(copy_icon)
    copy_btn.get_style_context().add_class("flat")
    copy_btn.set_tooltip_text("Copy from clipboard")
    copy_btn.connect("clicked", on_copy_from_clicked)
    header_bar.pack_start(copy_btn)

    # About button
    about_icon = Gtk.Image.new_from_icon_name("help-about-symbolic")
    about_btn = Gtk.Button()
    about_btn.get_style_context().add_class("flat")
    about_btn.set_child(about_icon)
    about_btn.set_tooltip_text("About Gradia")
    about_btn.connect("clicked", on_about_clicked)
    header_bar.pack_end(about_btn)

    # Save button
    save_btn = Gtk.Button()
    save_btn.get_style_context().add_class("suggested-action")
    save_btn.connect("clicked", on_save_clicked)

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    icon = Gtk.Image.new_from_icon_name("document-save-symbolic")
    label = Gtk.Label(label="Save Image")
    box.append(icon)
    box.append(label)
    save_btn.set_child(box)
    save_btn.set_sensitive(False)
    save_btn_ref[0] = save_btn

    # Copy to clipboard button (right)
    copy_right_icon = Gtk.Image.new_from_icon_name("edit-copy-symbolic")
    copy_right_btn = Gtk.Button()
    copy_right_btn.set_child(copy_right_icon)
    copy_right_btn.get_style_context().add_class("suggested-action")
    copy_right_btn.set_tooltip_text("Copy to Clipboard")
    copy_right_btn.set_sensitive(False)
    copy_right_btn.connect("clicked", on_copy_to_clicked)
    save_btn_ref[1] = copy_right_btn

    # Group the two buttons in a box
    right_buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    right_buttons_box.get_style_context().add_class("linked")
    right_buttons_box.append(save_btn)
    right_buttons_box.append(copy_right_btn)

    header_bar.pack_end(right_buttons_box)
    return header_bar


def create_image_stack(on_file_dropped, on_open_clicked):
    stack = Gtk.Stack()
    stack.set_vexpand(True)
    stack.set_hexpand(True)

    # Picture widget
    picture = Gtk.Picture()
    picture.set_content_fit(Gtk.ContentFit.CONTAIN)
    picture.set_can_shrink(True)
    stack.add_named(picture, "image")

    # Loading spinner
    spinner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    spinner_box.set_valign(Gtk.Align.CENTER)
    spinner_box.set_halign(Gtk.Align.CENTER)
    spinner_box.set_spacing(0)
    spinner_box.set_margin_top(20)
    spinner_box.set_margin_bottom(20)
    spinner_box.set_margin_start(20)
    spinner_box.set_margin_end(20)

    spinner = Gtk.Spinner()
    spinner.set_vexpand(False)
    spinner.set_hexpand(False)
    spinner_box.append(spinner)
    stack.add_named(spinner_box, "loading")

    # Drop target for drag & drop
    drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
    drop_target.set_preload(True)
    drop_target.connect("drop", on_file_dropped)
    stack.add_controller(drop_target)

    # Status page for no image loaded
    status_page = Adw.StatusPage()
    status_page.set_icon_name("image-x-generic-symbolic")
    status_page.set_title("No Image Loaded")
    status_page.set_description("Drag and drop one here")

    open_status_btn = Gtk.Button(label="Open Image...")
    open_status_btn.set_halign(Gtk.Align.CENTER)
    open_status_btn.get_style_context().add_class("suggested-action")
    open_status_btn.get_style_context().add_class("pill")
    open_status_btn.get_style_context().add_class("text-button")
    open_status_btn.connect("clicked", on_open_clicked)
    status_page.set_child(open_status_btn)

    stack.add_named(status_page, "empty")
    stack.set_visible_child_name("empty")

    return stack, picture, spinner

def create_image_options_group(padding, on_padding_changed, on_aspect_ratio_changed):
    padding_group = Adw.PreferencesGroup(title="Image Options")

    padding_row = Adw.ActionRow(title="Padding")
    padding_adjustment = Gtk.Adjustment(value=padding, lower=-50, upper=500, step_increment=10, page_increment=50)
    padding_spinner = Gtk.SpinButton(adjustment=padding_adjustment, numeric=True, valign=Gtk.Align.CENTER)
    padding_spinner.connect("value-changed", on_padding_changed)
    padding_row.add_suffix(padding_spinner)
    padding_group.add(padding_row)

    aspect_ratio_row = Adw.ActionRow(title="Aspect Ratio")
    aspect_ratio_entry = Gtk.Entry(placeholder_text="16:9", valign=Gtk.Align.CENTER)
    aspect_ratio_entry.connect("changed", on_aspect_ratio_changed)
    aspect_ratio_row.add_suffix(aspect_ratio_entry)
    padding_group.add(aspect_ratio_row)

    return padding_group, padding_spinner, aspect_ratio_entry


def create_text_overlay_group(available_fonts, on_text_changed, on_font_changed,
                               text_color="white", on_text_color_changed=None,
                               text_size=42, on_text_size_changed=None,
                               text_gravity="south", on_text_gravity_changed=None):
    text_group = Adw.PreferencesGroup(title="Text Overlay")

    # Text entry
    text_entry_row = Adw.ActionRow(title="Text")
    text_entry = Gtk.Entry(placeholder_text="Enter text")
    text_entry.set_valign(Gtk.Align.CENTER)
    text_entry.connect("changed", on_text_changed)
    text_entry_row.add_suffix(text_entry)
    text_group.add(text_entry_row)

    # Font selector
    font_row = Adw.ActionRow(title="Font")
    font_store = Gtk.ListStore(str)
    default_font_index = 0
    for i, font in enumerate(available_fonts):
        font_store.append([font])
        if font == "Adwaita-Sans":
            default_font_index = i
    font_combo = Gtk.ComboBoxText.new_with_entry()
    font_combo.set_valign(Gtk.Align.CENTER)
    font_combo.set_model(font_store)
    font_combo.set_entry_text_column(0)
    font_combo.set_active(default_font_index)
    font_combo.connect("changed", on_font_changed)
    font_row.add_suffix(font_combo)
    text_group.add(font_row)

    # Color selector
    color_row = Adw.ActionRow(title="Color")
    color_button = Gtk.ColorButton()
    rgba = Gdk.RGBA()
    rgba.parse(text_color)
    color_button.set_valign(Gtk.Align.CENTER)
    color_button.set_rgba(rgba)
    if on_text_color_changed:
        color_button.connect("color-set", on_text_color_changed)
    color_row.add_suffix(color_button)
    text_group.add(color_row)

    # Size selector
    size_row = Adw.ActionRow(title="Size")
    size_spin = Gtk.SpinButton.new_with_range(10, 100, 1)
    size_spin.set_valign(Gtk.Align.CENTER)
    size_spin.set_value(text_size)
    if on_text_size_changed:
        size_spin.connect("value-changed", on_text_size_changed)
    size_row.add_suffix(size_spin)
    text_group.add(size_row)

    # Gravity selector
    gravity_row = Adw.ActionRow(title="Gravity")
    gravity_combo = Gtk.ComboBoxText.new()
    gravity_combo.set_valign(Gtk.Align.CENTER)
    gravity_options = ["northwest", "north", "northeast", "west", "center", "east", "southwest", "south", "southeast"]
    for gravity in gravity_options:
        gravity_combo.append_text(gravity)
    gravity_combo.set_active(gravity_options.index(text_gravity) if text_gravity in gravity_options else 7)
    if on_text_gravity_changed:
        gravity_combo.connect("changed", on_text_gravity_changed)
    gravity_row.add_suffix(gravity_combo)
    text_group.add(gravity_row)

    return text_group, text_entry, font_combo, color_button, size_spin, gravity_combo


def create_file_info_group():
    file_info_group = Adw.PreferencesGroup(title="Current File")

    filename_row = Adw.ActionRow(title="Name", subtitle="No file loaded")
    location_row = Adw.ActionRow(title="Location", subtitle="No file loaded")
    processed_size_row = Adw.ActionRow(title="Modified image size", subtitle="N/A")

    file_info_group.add(filename_row)
    file_info_group.add(location_row)
    file_info_group.add(processed_size_row)

    return file_info_group, filename_row, location_row, processed_size_row


def create_sidebar_ui(
    gradient_selector_widget, padding, on_padding_changed, on_aspect_ratio_changed,
    on_text_changed, available_fonts, on_font_changed, text_color,
    on_text_color_changed, text_size, on_text_size_changed,
    text_gravity, on_text_gravity_changed
):
    sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    settings_scroll = Gtk.ScrolledWindow( vexpand=True)
    controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20,
                           margin_start=16, margin_end=16, margin_top=16, margin_bottom=16)

    controls_box.append(gradient_selector_widget)

    # Add grouped UI elements
    padding_group, padding_spinner, aspect_ratio_entry = create_image_options_group(
        padding, on_padding_changed, on_aspect_ratio_changed)
    controls_box.append(padding_group)

    text_group, text_entry, font_combo, color_button, size_spin, gravity_combo = create_text_overlay_group(
        available_fonts, on_text_changed, on_font_changed, text_color,
        on_text_color_changed, text_size, on_text_size_changed,
        text_gravity, on_text_gravity_changed)
    controls_box.append(text_group)

    file_info_group, filename_row, location_row, processed_size_row = create_file_info_group()
    controls_box.append(file_info_group)

    settings_scroll.set_child(controls_box)
    sidebar_box.append(settings_scroll)

    return {
        'sidebar': sidebar_box,
        'filename_row': filename_row,
        'location_row': location_row,
        'processed_size_row': processed_size_row,
        'padding_spinner': padding_spinner,
        'aspect_ratio_entry': aspect_ratio_entry,
        'text_entry': text_entry,
        'font_combo': font_combo,
        'color_button': color_button,
        'size_spin': size_spin,
        'gravity_combo': gravity_combo,
    }

def setup_shortcuts(win, on_open_clicked, on_save_clicked,on_paste,on_copy, save_btn):
    shortcut_controller = Gtk.ShortcutController()

    open_shortcut = Gtk.Shortcut.new(
        Gtk.ShortcutTrigger.parse_string("<Ctrl>O"),
        Gtk.CallbackAction.new(lambda *args: on_open_clicked(None))
    )
    save_shortcut = Gtk.Shortcut.new(
        Gtk.ShortcutTrigger.parse_string("<Ctrl>S"),
        Gtk.CallbackAction.new(
            lambda *args: on_save_clicked(None) if save_btn and save_btn.get_sensitive() else None
        )
    )

    copy_shortcut = Gtk.Shortcut.new(
        Gtk.ShortcutTrigger.parse_string("<Ctrl>C"),
        Gtk.CallbackAction.new(
            lambda *args: on_copy(None)
        )
    )

    paste_shortcut = Gtk.Shortcut.new(
        Gtk.ShortcutTrigger.parse_string("<Ctrl>V"),
        Gtk.CallbackAction.new(
            lambda *args: on_paste(None)
        )
    )

    shortcut_controller.add_shortcut(open_shortcut)
    shortcut_controller.add_shortcut(save_shortcut)
    shortcut_controller.add_shortcut(copy_shortcut)
    shortcut_controller.add_shortcut(paste_shortcut)
    win.add_controller(shortcut_controller)

def create_about_dialog():
    about = Adw.AboutDialog()
    about.set_application_name("Gradia")
    about.set_version("0.2")
    about.set_comments("Make your images ready for the world")
    about.set_website("https://github.com/AlexanderVanhee/Gradia")
    about.set_developer_name("Alexander Vanhee")
    about.set_application_icon("gradia")
    return about

