blueprints = custom_target('blueprints',
  input: files(
    'header_bar.blp',
    'controls_overlay.blp'
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@']
)