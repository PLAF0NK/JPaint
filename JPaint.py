import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QSpinBox, QPushButton, QColorDialog, QFileDialog, QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem, QInputDialog, QGraphicsRectItem, QGraphicsEllipseItem
from PyQt6.QtGui import QAction, QIcon, QPixmap, QPainter, QPen, QColor, QTransform, QKeySequence, QShortcut, QMouseEvent, QUndoStack, QUndoCommand
from PyQt6.QtCore import Qt, QPoint, QSize, QSettings, QPointF, QRect, QRectF
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from collections import deque
class UndoCommand(QUndoCommand):
 def __init__(self, canvas, old_pixmap, new_pixmap):
  super().__init__()
  self.canvas = canvas
  self.old_pixmap = old_pixmap
  self.new_pixmap = new_pixmap
 def undo(self):
  self.canvas.pixmap_item.setPixmap(self.old_pixmap)
  self.canvas.scene.update()
 def redo(self):
  self.canvas.pixmap_item.setPixmap(self.new_pixmap)
  self.canvas.scene.update()
class PaintCanvas(QGraphicsView):
 def __init__(self, width=800, height=800):
  super().__init__()
  self.scene = QGraphicsScene(self)
  self.setScene(self.scene)
  self.pixmap_item = QGraphicsPixmapItem()
  self.pixmap_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
  self.pixmap_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
  self.scene.addItem(self.pixmap_item)
  self.set_pixmap_size(width, height)
  self.setAlignment(Qt.AlignmentFlag.AlignCenter)
  self.brush_size = 5
  self.brush_color = QColor(Qt.GlobalColor.black)
  self.prev_color = QColor(Qt.GlobalColor.black)
  self.is_erasing = False
  self.is_filling = False
  self.is_dropping = False
  self.is_selecting = False
  self.last_pos = QPoint()
  self.offset = QPoint()
  self.saved_pixmap = None
  self.temp_pixmap = None
  self.drawing = False
  self.selection_rect_item = None
  self.selection_start = None
  self.is_selection_dragging = False
  self.is_shift_dragging = False
  self.selection_start_move = None
  self.resizing_handle_size = 8
  self.resizing_handles = []
  self.is_resizing = False
  self.resize_start_pos = None
  self.resize_start_rect = None
  self.resize_handle_index = None
  self.setRenderHint(QPainter.RenderHint.Antialiasing)
  self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
  self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
  self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
 def set_pixmap_size(self, width, height):
  pixmap = QPixmap(width, height)
  pixmap.fill(Qt.GlobalColor.white)
  self.pixmap_item.setPixmap(pixmap)
  self.scene.setSceneRect(0, 0, width, height)
 def set_brush_size(self, size):
  self.brush_size = size
 def set_brush_color(self, color):
  self.brush_color = color
  self.prev_color = color
  self.is_erasing = False
 def toggle_eraser(self):
  if self.is_erasing:
   self.is_erasing = False
   self.brush_color = self.prev_color
  else:
   self.prev_color = self.brush_color
   self.brush_color = QColor(Qt.GlobalColor.white)
   self.is_erasing = True
 def toggle_fill(self):
  self.is_filling = not self.is_filling
 def toggle_selection(self):
  self.is_selecting = not self.is_selecting
  if self.is_selecting:
   self.is_filling = False
   self.is_dropping = False
   self.setDragMode(QGraphicsView.DragMode.NoDrag)
  else:
   self.clear_selection()
 def clear_selection(self):
  if self.selection_rect_item:
   self.scene.removeItem(self.selection_rect_item)
   self.selection_rect_item = None
   self.selection_start = None
  self._remove_resize_handles()
 def _remove_resize_handles(self):
  for handle in self.resizing_handles:
   self.scene.removeItem(handle)
  self.resizing_handles = []
 def _update_resize_handles(self):
  if self.selection_rect_item and self.is_selection_active():
   rect = self.selection_rect_item.rect()
   self._remove_resize_handles()
   handles = []
   for x, y in [
    (rect.x(), rect.y()),
    (rect.x() + rect.width(), rect.y()),
    (rect.x(), rect.y() + rect.height()),
    (rect.x() + rect.width(), rect.y() + rect.height())
   ]:
    handle = QGraphicsRectItem(x - self.resizing_handle_size/2, y - self.resizing_handle_size/2,
            self.resizing_handle_size, self.resizing_handle_size)
    handle.setBrush(QColor(0, 120, 215))
    handle.setPen(QPen(Qt.GlobalColor.black, 1))
    handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
    handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
    handle.setZValue(1001)
    self.scene.addItem(handle)
    handles.append(handle)
   self.resizing_handles = handles
  else:
   self._remove_resize_handles()
 def _is_handle_clicked(self, pos):
  if not self.resizing_handles:
   return None
  for i, handle in enumerate(self.resizing_handles):
   if handle.rect().contains(handle.mapFromScene(pos)):
    return i
  return None
 def start_selection(self, x, y):
  self.selection_start = QPoint(int(x), int(y))
  if self.selection_rect_item:
   self.scene.removeItem(self.selection_rect_item)
  self._remove_resize_handles()
  self.selection_rect_item = QGraphicsRectItem(x, y, 1, 1)
  pen = QPen(Qt.GlobalColor.blue, 2, Qt.PenStyle.DashLine)
  self.selection_rect_item.setPen(pen)
  self.selection_rect_item.setBrush(QColor(255, 255, 0, 50))
  self.selection_rect_item.setZValue(1000)
  self.scene.addItem(self.selection_rect_item)
 def update_selection(self, x, y):
  if not self.selection_start or not self.selection_rect_item:
   return
  x1 = min(self.selection_start.x(), int(x))
  y1 = min(self.selection_start.y(), int(y))
  x2 = max(self.selection_start.x(), int(x))
  y2 = max(self.selection_start.y(), int(y))
  self.selection_rect_item.setRect(x1, y1, x2 - x1, y2 - y1)
  self._update_resize_handles()
 def finalize_selection(self):
  pass
 def get_selection_rect(self):
  if self.selection_rect_item:
   rect = self.selection_rect_item.rect()
   return QRect(int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()))
  return None
 def is_point_in_selection(self, x, y):
  selection = self.get_selection_rect()
  if selection and selection.width() > 0 and selection.height() > 0:
   return selection.x() <= x <= selection.x() + selection.width() and \
       selection.y() <= y <= selection.y() + selection.height()
  return True
 def clear_canvas(self):
  pixmap = self.pixmap_item.pixmap()
  old_pixmap = pixmap.copy()
  pixmap.fill(Qt.GlobalColor.white)
  self.pixmap_item.setPixmap(pixmap)
  self.pixmap_item.update()
  return old_pixmap, pixmap
 def zoom(self, factor):
  self.scale(factor, factor)
 def reset_zoom(self):
  self.resetTransform()
 def mousePressEvent(self, event):
  if event.button() == Qt.MouseButton.LeftButton:
   scene_pos = self.mapToScene(event.pos())
   if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
    self.is_dropping = True
    self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
    self.last_pos = event.pos()
   elif self.is_selecting:
    handle_index = self._is_handle_clicked(scene_pos)
    if handle_index is not None:
     self.is_resizing = True
     self.resize_start_pos = scene_pos
     self.resize_start_rect = self.selection_rect_item.rect()
     self.resize_handle_index = handle_index
    else:
     self.start_selection(scene_pos.x(), scene_pos.y())
     self.is_selection_dragging = True
     self.last_pos = event.pos()
   elif event.modifiers() == Qt.KeyboardModifier.ShiftModifier and self.is_selection_active():
    self.is_shift_dragging = True
    self.selection_start_move = scene_pos
    self.last_pos = event.pos()
   elif self.is_filling:
    pos = self.mapToScene(event.pos())
    if self.is_selection_active():
     selection = self.get_selection_rect()
     if selection:
      x, y = int(pos.x()), int(pos.y())
      if self.is_point_in_selection(x, y):
       self.fill_area(x, y)
    else:
     self.fill_area(int(pos.x()), int(pos.y()))
   else:
    self.drawing = True
    self.last_pos = event.pos()
    self.temp_pixmap = self.pixmap_item.pixmap().copy()
 def mouseMoveEvent(self, event):
  if self.is_dropping:
   delta = event.pos() - self.last_pos
   self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
   self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
   self.last_pos = event.pos()
  elif self.is_selecting and self.is_selection_dragging:
   pos = self.mapToScene(event.pos())
   self.update_selection(self.selection_start.x(), self.selection_start.y())
   self.update_selection(pos.x(), pos.y())
  elif self.is_resizing and self.selection_rect_item:
   pos = self.mapToScene(event.pos())
   rect = self.resize_start_rect
   delta = pos - self.resize_start_pos
   new_x = rect.x()
   new_y = rect.y()
   new_width = rect.width()
   new_height = rect.height()
   if self.resize_handle_index == 0:
    new_x = rect.x() + delta.x()
    new_y = rect.y() + delta.y()
    new_width = rect.width() - delta.x()
    new_height = rect.height() - delta.y()
   elif self.resize_handle_index == 1:
    new_y = rect.y() + delta.y()
    new_width = rect.width() + delta.x()
    new_height = rect.height() - delta.y()
   elif self.resize_handle_index == 2:
    new_x = rect.x() + delta.x()
    new_width = rect.width() - delta.x()
    new_height = rect.height() + delta.y()
   elif self.resize_handle_index == 3:
    new_width = rect.width() + delta.x()
    new_height = rect.height() + delta.y()
   min_size = 5
   if new_width < min_size:
    new_width = min_size
   if new_height < min_size:
    new_height = min_size
   self.selection_rect_item.setRect(new_x, new_y, new_width, new_height)
   self._update_resize_handles()
  elif self.is_shift_dragging and self.is_selection_active():
   pos = self.mapToScene(event.pos())
   delta = pos - self.selection_start_move
   rect = self.selection_rect_item.rect()
   self.selection_rect_item.setRect(rect.x() + delta.x(), rect.y() + delta.y(), rect.width(), rect.height())
   self._update_resize_handles()
   self.selection_start_move = pos
  elif self.drawing and event.buttons() == Qt.MouseButton.LeftButton:
   pos = self.mapToScene(event.pos())
   if self.is_selection_active():
    selection = self.get_selection_rect()
    if selection:
     x, y = int(pos.x()), int(pos.y())
     if self.is_point_in_selection(x, y):
      scene_pos = self.mapToScene(self.last_pos)
      self.draw_line(QPoint(int(scene_pos.x()), int(scene_pos.y())), QPointF(x, y))
   else:
    scene_pos = self.mapToScene(self.last_pos)
    self.draw_line(QPoint(int(scene_pos.x()), int(scene_pos.y())), pos)
   self.last_pos = event.pos()
 def mouseReleaseEvent(self, event):
  if event.button() == Qt.MouseButton.LeftButton:
   if self.is_selecting and self.is_selection_dragging:
    self.is_selection_dragging = False
    self.finalize_selection()
   elif self.is_resizing:
    self.is_resizing = False
    new_pixmap = self.pixmap_item.pixmap().copy()
    old_pixmap = self.temp_pixmap
    self.undo_stack.push(UndoCommand(self, old_pixmap, new_pixmap))
   elif self.is_shift_dragging:
    self.is_shift_dragging = False
    new_pixmap = self.pixmap_item.pixmap().copy()
    old_pixmap = self.temp_pixmap
    self.undo_stack.push(UndoCommand(self, old_pixmap, new_pixmap))
   elif self.drawing:
    self.drawing = False
    new_pixmap = self.pixmap_item.pixmap().copy()
    old_pixmap = self.temp_pixmap
    self.undo_stack.push(UndoCommand(self, old_pixmap, new_pixmap))
   if self.is_dropping:
    self.is_dropping = False
    self.setDragMode(QGraphicsView.DragMode.NoDrag)
 def wheelEvent(self, event):
  if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
   factor = 1.1 if event.angleDelta().y() > 0 else 0.9
   self.zoom(factor)
  else:
   super().wheelEvent(event)
 def keyPressEvent(self, event):
  if event.key() == Qt.Key.Key_Delete:
   if self.is_selection_active():
    selection = self.get_selection_rect()
    if selection:
     pixmap = self.pixmap_item.pixmap()
     old_pixmap = pixmap.copy()
     painter = QPainter(pixmap)
     painter.setPen(QPen(Qt.GlobalColor.white, self.brush_size))
     painter.setBrush(Qt.GlobalColor.white)
     painter.drawRect(selection)
     painter.end()
     self.pixmap_item.setPixmap(pixmap)
     self.pixmap_item.update()
     self.undo_stack.push(UndoCommand(self, old_pixmap, pixmap))
     self.clear_selection()
   else:
    old_pixmap, new_pixmap = self.clear_canvas()
    self.undo_stack.push(UndoCommand(self, old_pixmap, new_pixmap))
  super().keyPressEvent(event)
 def is_selection_active(self):
  if self.selection_rect_item:
   rect = self.selection_rect_item.rect()
   return rect.width() > 0 and rect.height() > 0
  return False
 def draw_line(self, start, end):
  pixmap = self.pixmap_item.pixmap()
  painter = QPainter(pixmap)
  painter.setPen(self._get_pen())
  start_point = start.toPoint() if isinstance(start, QPointF) else start
  end_point = end.toPoint() if isinstance(end, QPointF) else end
  if self.is_selection_active():
   selection = self.get_selection_rect()
   if selection:
    line_x1 = max(start_point.x(), selection.x())
    line_y1 = max(start_point.y(), selection.y())
    line_x2 = min(end_point.x(), selection.x() + selection.width())
    line_y2 = min(end_point.y(), selection.y() + selection.height())
    if line_x1 < line_x2 and line_y1 < line_y2:
     painter.drawLine(line_x1, line_y1, line_x2, line_y2)
  else:
   painter.drawLine(start_point, end_point)
  painter.end()
  self.pixmap_item.setPixmap(pixmap)
  self.pixmap_item.update()
 def _get_pen(self):
  pen = QPen()
  pen.setWidth(self.brush_size)
  if self.is_erasing:
   pen.setColor(Qt.GlobalColor.white)
  else:
   pen.setColor(self.brush_color)
  pen.setCapStyle(Qt.PenCapStyle.RoundCap)
  pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
  return pen
 def fill_area(self, x, y):
  pixmap = self.pixmap_item.pixmap()
  if pixmap.isNull():
   return
  if x < 0 or x >= pixmap.width() or y < 0 or y >= pixmap.height():
   return
  if self.is_selection_active():
   selection = self.get_selection_rect()
   if selection:
    if not (selection.x() <= x <= selection.x() + selection.width() and
      selection.y() <= y <= selection.y() + selection.height()):
     return
  target_color = pixmap.toImage().pixelColor(x, y)
  if target_color == self.brush_color:
   return
  old_pixmap = pixmap.copy()
  image = pixmap.toImage()
  image = image.convertToFormat(image.Format.Format_ARGB32)
  target_rgba = target_color.rgba()
  fill_rgba = self.brush_color.rgba()
  width, height = image.width(), image.height()
  queue = deque()
  queue.append(QPoint(x, y))
  image.setPixel(x, y, fill_rgba)
  max_iterations = width * height
  iterations = 0
  while queue and iterations < max_iterations:
   iterations += 1
   current_point = queue.popleft()
   neighbors = [
    QPoint(current_point.x() + 1, current_point.y()),
    QPoint(current_point.x() - 1, current_point.y()),
    QPoint(current_point.x(), current_point.y() + 1),
    QPoint(current_point.x(), current_point.y() - 1)
   ]
   for neighbor in neighbors:
    if self.is_selection_active():
     selection = self.get_selection_rect()
     if selection:
      if not (selection.x() <= neighbor.x() <= selection.x() + selection.width() and
        selection.y() <= neighbor.y() <= selection.y() + selection.height()):
       continue
    if (0 <= neighbor.x() < width and
     0 <= neighbor.y() < height and
     image.pixel(neighbor.x(), neighbor.y()) == target_rgba and
     image.pixel(neighbor.x(), neighbor.y()) != fill_rgba):
     image.setPixel(neighbor.x(), neighbor.y(), fill_rgba)
     queue.append(neighbor)
  new_pixmap = QPixmap.fromImage(image)
  self.pixmap_item.setPixmap(new_pixmap)
  self.pixmap_item.update()
  self.undo_stack.push(UndoCommand(self, old_pixmap, new_pixmap))
class PaintApp(QMainWindow):
 def __init__(self):
  super().__init__()
  self.current_file = None
  self.undo_stack = QUndoStack(self)
  self.init_ui()
  self.load_settings()
 def init_ui(self):
  self.setWindowTitle("JPaint - Новый рисунок")
  self.setGeometry(100, 100, 1000, 800)
  self.canvas = PaintCanvas()
  self.canvas.undo_stack = self.undo_stack
  self.setCentralWidget(self.canvas)
  self.create_toolbar()
  self.create_menu()
  self.create_context_menu()
  self.shortcut_copy = QShortcut(QKeySequence("Ctrl+C"), self)
  self.shortcut_copy.activated.connect(self.copy_to_clipboard)
  self.shortcut_paste = QShortcut(QKeySequence("Ctrl+V"), self)
  self.shortcut_paste.activated.connect(self.paste_from_clipboard)
  self.shortcut_cut = QShortcut(QKeySequence("Ctrl+X"), self)
  self.shortcut_cut.activated.connect(self.cut_selection)
 def create_toolbar(self):
  toolbar = QToolBar("Инструменты")
  toolbar.setMovable(False)
  self.size_spin = QSpinBox()
  self.size_spin.setRange(1, 100)
  self.size_spin.setValue(5)
  self.size_spin.valueChanged.connect(self.canvas.set_brush_size)
  toolbar.addWidget(self.size_spin)
  toolbar.addSeparator()
  self.color_btn = QPushButton()
  self.color_btn.setFixedSize(30, 30)
  self.color_btn.setStyleSheet("background-color: black; border: 2px solid gray; border-radius: 5px;")
  self.color_btn.clicked.connect(self.choose_color)
  toolbar.addWidget(self.color_btn)
  toolbar.addSeparator()
  self.eraser_btn = QPushButton("Ластик")
  self.eraser_btn.setCheckable(True)
  self.eraser_btn.clicked.connect(self.toggle_eraser)
  toolbar.addWidget(self.eraser_btn)
  toolbar.addSeparator()
  self.fill_btn = QPushButton("Заливка")
  self.fill_btn.setCheckable(True)
  self.fill_btn.clicked.connect(self.toggle_fill)
  toolbar.addWidget(self.fill_btn)
  toolbar.addSeparator()
  self.selection_btn = QPushButton("Выделение")
  self.selection_btn.setCheckable(True)
  self.selection_btn.clicked.connect(self.toggle_selection)
  toolbar.addWidget(self.selection_btn)
  toolbar.addSeparator()
  clear_btn = QPushButton("Очистить")
  clear_btn.clicked.connect(self.canvas.clear_canvas)
  toolbar.addWidget(clear_btn)
  self.addToolBar(toolbar)
 def create_menu(self):
  menubar = self.menuBar()
  file_menu = menubar.addMenu("Файл")
  new_action = QAction("Новый", self)
  new_action.setShortcut("Ctrl+N")
  new_action.triggered.connect(self.new_file)
  file_menu.addAction(new_action)
  open_action = QAction("Открыть...", self)
  open_action.setShortcut("Ctrl+O")
  open_action.triggered.connect(self.open_file)
  file_menu.addAction(open_action)
  save_action = QAction("Сохранить", self)
  save_action.setShortcut("Ctrl+S")
  save_action.triggered.connect(self.save_file)
  file_menu.addAction(save_action)
  save_as_action = QAction("Сохранить как...", self)
  save_as_action.setShortcut("Ctrl+Shift+S")
  save_as_action.triggered.connect(self.save_file_as)
  file_menu.addAction(save_as_action)
  file_menu.addSeparator()
  print_action = QAction("Печать...", self)
  print_action.setShortcut("Ctrl+P")
  print_action.triggered.connect(self.print_file)
  file_menu.addAction(print_action)
  file_menu.addSeparator()
  exit_action = QAction("Выход", self)
  exit_action.setShortcut("Ctrl+Q")
  exit_action.triggered.connect(self.close)
  file_menu.addAction(exit_action)
  edit_menu = menubar.addMenu("Правка")
  undo_action = QAction("Отменить", self)
  undo_action.setShortcut("Ctrl+Z")
  undo_action.triggered.connect(self.undo_stack.undo)
  edit_menu.addAction(undo_action)
  redo_action = QAction("Вернуть", self)
  redo_action.setShortcut("Ctrl+Y")
  redo_action.triggered.connect(self.undo_stack.redo)
  edit_menu.addAction(redo_action)
  edit_menu.addSeparator()
  size_action = QAction("Размер кисти...", self)
  size_action.triggered.connect(self.change_brush_size)
  edit_menu.addAction(size_action)
  color_action = QAction("Цвет...", self)
  color_action.triggered.connect(self.choose_color)
  edit_menu.addAction(color_action)
  self.fill_menu_action = QAction("Заливка", self)
  self.fill_menu_action.setCheckable(True)
  self.fill_menu_action.triggered.connect(self.toggle_fill)
  edit_menu.addAction(self.fill_menu_action)
  self.selection_menu_action = QAction("Выделение", self)
  self.selection_menu_action.setCheckable(True)
  self.selection_menu_action.triggered.connect(self.toggle_selection)
  edit_menu.addAction(self.selection_menu_action)
  edit_menu.addSeparator()
  clear_action = QAction("Очистить холст", self)
  clear_action.setShortcut("")
  clear_action.triggered.connect(self.canvas.clear_canvas)
  edit_menu.addAction(clear_action)
  view_menu = menubar.addMenu("Вид")
  zoom_in_action = QAction("Увеличить", self)
  zoom_in_action.setShortcut("Ctrl++")
  zoom_in_action.triggered.connect(lambda: self.canvas.zoom(1.1))
  view_menu.addAction(zoom_in_action)
  zoom_out_action = QAction("Уменьшить", self)
  zoom_out_action.setShortcut("Ctrl+-")
  zoom_out_action.triggered.connect(lambda: self.canvas.zoom(0.9))
  view_menu.addAction(zoom_out_action)
  zoom_reset_action = QAction("Сбросить масштаб", self)
  zoom_reset_action.setShortcut("Ctrl+0")
  zoom_reset_action.triggered.connect(self.canvas.reset_zoom)
  view_menu.addAction(zoom_reset_action)
  help_menu = menubar.addMenu("Справка")
  about_action = QAction("О программе", self)
  about_action.triggered.connect(self.show_about)
  help_menu.addAction(about_action)
 def create_context_menu(self):
  self.canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
  clear_action = QAction("Очистить холст", self)
  clear_action.triggered.connect(self.canvas.clear_canvas)
  self.canvas.addAction(clear_action)
  size_action = QAction("Размер кисти...", self)
  size_action.triggered.connect(self.change_brush_size)
  self.canvas.addAction(size_action)
  color_action = QAction("Цвет...", self)
  color_action.triggered.connect(self.choose_color)
  self.canvas.addAction(color_action)
  self.context_fill_action = QAction("Заливка", self)
  self.context_fill_action.setCheckable(True)
  self.context_fill_action.triggered.connect(self.toggle_fill)
  self.canvas.addAction(self.context_fill_action)
  self.context_selection_action = QAction("Выделение", self)
  self.context_selection_action.setCheckable(True)
  self.context_selection_action.triggered.connect(self.toggle_selection)
  self.canvas.addAction(self.context_selection_action)
 def new_file(self):
  size_tuple, ok = QInputDialog.getText(
   self, "Новый рисунок", "Введите размеры (ширина x высота):", text="800x800"
  )
  if ok and "x" in size_tuple:
   try:
    width, height = map(int, size_tuple.split("x"))
    self.canvas.set_pixmap_size(width, height)
    self.current_file = None
    self.setWindowTitle(f"JPaint - Новый рисунок")
   except ValueError:
    QMessageBox.warning(self, "Ошибка", "Неверный формат. Используйте: ширина x высота")
 def open_file(self):
  file_path, _ = QFileDialog.getOpenFileName(
   self, "Открыть изображение", "", "Изображения (*.png *.jpg *.bmp *.jpeg)"
  )
  if file_path:
   pixmap = QPixmap(file_path)
   if not pixmap.isNull():
    self.canvas.pixmap_item.setPixmap(pixmap)
    self.canvas.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
    self.current_file = file_path
    self.setWindowTitle(f"JPaint - {file_path}")
   else:
    QMessageBox.warning(self, "Ошибка", "Не удалось открыть изображение")
 def save_file(self):
  if not self.current_file:
   self.save_file_as()
  else:
   self._save_pixmap(self.current_file)
 def save_file_as(self):
  file_path, _ = QFileDialog.getSaveFileName(
   self, "Сохранить изображение как", "", "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)"
  )
  if file_path:
   self.current_file = file_path
   self._save_pixmap(file_path)
   self.setWindowTitle(f"JPaint - {file_path}")
 def _save_pixmap(self, file_path):
  pixmap = self.canvas.pixmap_item.pixmap()
  if not pixmap.save(file_path):
   QMessageBox.warning(self, "Ошибка", "Не удалось сохранить изображение")
 def print_file(self):
  pixmap = self.canvas.pixmap_item.pixmap()
  printer = QPrinter(QPrinter.PrinterMode.HighResolution)
  dialog = QPrintDialog(printer, self)
  if dialog.exec() == QPrintDialog.DialogCode.Accepted:
   painter = QPainter(printer)
   pixmap.render(painter)
   painter.end()
 def change_brush_size(self):
  size, ok = QInputDialog.getInt(
   self, "Размер кисти", "Введите размер кисти (1-100):",
   self.canvas.brush_size, 1, 100
  )
  if ok:
   self.canvas.set_brush_size(size)
   self.size_spin.setValue(size)
 def choose_color(self):
  color = QColorDialog.getColor(self.canvas.brush_color, self)
  if color.isValid():
   self.canvas.set_brush_color(color)
   self.color_btn.setStyleSheet(f"background-color: {color.name()}; border: 2px solid gray; border-radius: 5px;")
 def show_about(self):
  QMessageBox.about(
   self,
   "О программе",
   "JPaint - простой переносной графический редактор\n\n"
   "Версия: 1.0\n"
   "Автор: PLAF0NK\n\n"
   "Навигация:\n"
   "Ctrl+ЛКМ - перетаскивание холста\n"
   "Ctrl+ЦКМ - масштаб\n"
   "ПКМ - контекстное меню\n"
   "Del - очистить холст"
  )
 def load_settings(self):
  settings = QSettings("PLAF0NK", "JPaint")
  brush_size = settings.value("brush_size", 5)
  self.canvas.set_brush_size(int(brush_size))
  self.size_spin.setValue(int(brush_size))
  color = settings.value("brush_color", "#000000")
  self.canvas.set_brush_color(QColor(color))
  self.color_btn.setStyleSheet(f"background-color: {color}; border: 2px solid gray; border-radius: 5px;")
 def save_settings(self):
  settings = QSettings("PLAF0NK", "JPaint")
  settings.setValue("brush_size", self.canvas.brush_size)
  settings.setValue("brush_color", self.canvas.brush_color.name())
 def closeEvent(self, event):
  self.save_settings()
  super().closeEvent(event)
 def copy_to_clipboard(self):
  if self.canvas.is_selection_active():
   selection = self.canvas.get_selection_rect()
   if selection:
    pixmap = self.canvas.pixmap_item.pixmap()
    cropped_pixmap = pixmap.copy(selection)
    QApplication.clipboard().setPixmap(cropped_pixmap)
  else:
   QApplication.clipboard().setPixmap(self.canvas.pixmap_item.pixmap())
 def paste_from_clipboard(self):
  clipboard = QApplication.clipboard()
  if clipboard.mimeData().hasImage():
   pixmap = clipboard.pixmap()
   if not pixmap.isNull():
    canvas_rect = self.canvas.scene.sceneRect()
    x = (canvas_rect.width() - pixmap.width()) / 2
    y = (canvas_rect.height() - pixmap.height()) / 2
    self.canvas.pixmap_item.setPixmap(pixmap)
    self.canvas.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
    self.current_file = None
    self.setWindowTitle("JPaint - Вставлено из буфера")
 def cut_selection(self):
  if self.canvas.is_selection_active():
   selection = self.canvas.get_selection_rect()
   if selection:
    pixmap = self.canvas.pixmap_item.pixmap()
    old_pixmap = pixmap.copy()
    cropped_pixmap = pixmap.copy(selection)
    QApplication.clipboard().setPixmap(cropped_pixmap)
    painter = QPainter(pixmap)
    painter.setPen(QPen(Qt.GlobalColor.white, 1))
    painter.setBrush(Qt.GlobalColor.white)
    painter.drawRect(selection)
    painter.end()
    self.canvas.pixmap_item.setPixmap(pixmap)
    self.canvas.pixmap_item.update()
    self.canvas.undo_stack.push(UndoCommand(self.canvas, old_pixmap, pixmap))
    self.canvas.clear_selection()
  else:
   old_pixmap = self.canvas.pixmap_item.pixmap().copy()
   new_pixmap = QPixmap(old_pixmap.size())
   new_pixmap.fill(Qt.GlobalColor.white)
   self.canvas.pixmap_item.setPixmap(new_pixmap)
   QApplication.clipboard().setPixmap(old_pixmap)
   self.canvas.undo_stack.push(UndoCommand(self.canvas, old_pixmap, new_pixmap))
 def toggle_eraser(self):
  self.canvas.toggle_eraser()
  self.eraser_btn.setChecked(self.canvas.is_erasing)
 def toggle_fill(self):
  self.canvas.toggle_fill()
  self.fill_btn.setChecked(self.canvas.is_filling)
  self.fill_menu_action.setChecked(self.canvas.is_filling)
  self.context_fill_action.setChecked(self.canvas.is_filling)
 def toggle_selection(self):
  self.canvas.toggle_selection()
  self.selection_btn.setChecked(self.canvas.is_selecting)
  self.selection_menu_action.setChecked(self.canvas.is_selecting)
  self.context_selection_action.setChecked(self.canvas.is_selecting)
app = QApplication(sys.argv)
app.setApplicationName("JPaint")
app.setOrganizationName("PLAF0NK")
paint_app = PaintApp()
paint_app.show()
sys.exit(app.exec())