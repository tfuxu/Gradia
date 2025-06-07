blueprints = custom_target('blueprints',
  input: files(
    'controls_overlay.blp',
    'home_bar.blp',
    'image_sidebar.blp',
    'recent_picker.blp',
    'text_entry_popover.blp',
    'welcome_page.blp'
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@']
)
