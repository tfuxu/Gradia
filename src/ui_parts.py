import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Adw, Gdk, GLib

def create_header_bar(save_btn_ref, on_open_clicked, on_about_clicked, on_save_clicked):
    header_bar = Adw.HeaderBar()

    # Open button
    open_icon = Gtk.Image.new_from_icon_name("document-open-symbolic")
    open_btn = Gtk.Button()
    open_btn.set_child(open_icon)
    open_btn.get_style_context().add_class("flat")
    open_btn.set_tooltip_text("Open Image")
    open_btn.connect("clicked", on_open_clicked)
    header_bar.pack_start(open_btn)

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
    header_bar.pack_end(save_btn)

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

def create_sidebar_ui(gradient_selector_widget, padding, on_padding_changed, on_aspect_ratio_changed):
    sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

    settings_scroll = Gtk.ScrolledWindow()
    settings_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    settings_scroll.set_vexpand(True)

    controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
    controls_box.set_margin_start(16)
    controls_box.set_margin_end(16)
    controls_box.set_margin_top(16)
    controls_box.set_margin_bottom(16)

    # Add the gradient selector widget
    controls_box.append(gradient_selector_widget)

    # Image Options Group
    padding_group = Adw.PreferencesGroup()
    padding_group.set_title("Image Options")

    padding_row = Adw.ActionRow()
    padding_row.set_title("Padding")

    padding_adjustment = Gtk.Adjustment(value=padding, lower=-50, upper=500, step_increment=10, page_increment=50)
    padding_spinner = Gtk.SpinButton()
    padding_spinner.set_adjustment(padding_adjustment)
    padding_spinner.set_numeric(True)
    padding_spinner.connect("value-changed", on_padding_changed)
    padding_spinner.set_valign(Gtk.Align.CENTER)
    padding_row.add_suffix(padding_spinner)
    padding_group.add(padding_row)

    aspect_ratio_row = Adw.ActionRow()
    aspect_ratio_row.set_title("Aspect Ratio")

    aspect_ratio_entry = Gtk.Entry()
    aspect_ratio_entry.set_placeholder_text("16:9")
    aspect_ratio_entry.set_valign(Gtk.Align.CENTER)
    aspect_ratio_entry.connect("changed", on_aspect_ratio_changed)

    aspect_ratio_row.add_suffix(aspect_ratio_entry)
    padding_group.add(aspect_ratio_row)

    controls_box.append(padding_group)

    # File Info Group
    file_info_group = Adw.PreferencesGroup()
    file_info_group.set_title("Current File")

    filename_row = Adw.ActionRow()
    filename_row.set_title("Name")
    filename_row.set_subtitle("No file loaded")
    file_info_group.add(filename_row)

    location_row = Adw.ActionRow()
    location_row.set_title("Location")
    location_row.set_subtitle("No file loaded")
    file_info_group.add(location_row)

    processed_size_row = Adw.ActionRow()
    processed_size_row.set_title("Modified image size")
    processed_size_row.set_subtitle("N/A")
    file_info_group.add(processed_size_row)

    controls_box.append(file_info_group)

    settings_scroll.set_child(controls_box)
    sidebar_box.append(settings_scroll)

    sidebar_info = {
        'sidebar': sidebar_box,
        'filename_row': filename_row,
        'location_row': location_row,
        'processed_size_row': processed_size_row,
        'padding_spinner': padding_spinner,
        'aspect_ratio_entry': aspect_ratio_entry
    }

    return sidebar_info

def setup_shortcuts(win, on_open_clicked, on_save_clicked, save_btn):
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

    shortcut_controller.add_shortcut(open_shortcut)
    shortcut_controller.add_shortcut(save_shortcut)
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

