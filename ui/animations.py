"""Small, reusable Qt animations for the VPadConnect desktop UI.

Transitions are deliberately short and use snapshots for outgoing pages so the
actual controller/HID widgets are not forced through an expensive opacity effect.
Set VPADCONNECT_REDUCED_MOTION=1 to disable decorative animations.
"""
from __future__ import annotations

import os

from PySide6.QtCore import (
    QEvent,
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QObject,
    Property,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTabBar,
)


def animations_enabled() -> bool:
    """Return whether nonessential UI motion is enabled for this process."""
    if os.environ.get("VPADCONNECT_REDUCED_MOTION", "").strip().lower() in {
        "1", "true", "yes", "on",
    }:
        return False

    app = QApplication.instance()
    if app is not None and bool(app.property("reducedMotion")):
        return False
    return True


class AnimatedTabBar(QTabBar):
    """A native QTabBar with a smoothly moving indigo-to-cyan active indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._indicator_rect = QRect()
        self._indicator_animation = QPropertyAnimation(
            self, b"indicatorRect", self
        )
        self._indicator_animation.setDuration(260)
        self._indicator_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.currentChanged.connect(self._animate_indicator_to_index)

    def get_indicator_rect(self) -> QRect:
        return QRect(self._indicator_rect)

    def set_indicator_rect(self, rect: QRect) -> None:
        if rect == self._indicator_rect:
            return
        self._indicator_rect = QRect(rect)
        self.update()

    indicatorRect = Property(QRect, get_indicator_rect, set_indicator_rect)

    def _target_indicator_rect(self, index: int) -> QRect:
        if index < 0 or index >= self.count():
            center = self._indicator_rect.center().x() if not self._indicator_rect.isNull() else self.width() // 2
            return QRect(center, max(0, self.height() - 3), 0, 3)

        tab_rect = self.tabRect(index)
        if tab_rect.width() <= 0:
            return QRect()

        inset = min(14, max(6, tab_rect.width() // 5))
        width = max(12, tab_rect.width() - 2 * inset)
        return QRect(
            tab_rect.left() + (tab_rect.width() - width) // 2,
            max(0, self.height() - 3),
            width,
            3,
        )

    def _animate_indicator_to_index(self, index: int) -> None:
        target = self._target_indicator_rect(index)
        self._indicator_animation.stop()

        if (
            not animations_enabled()
            or not self.isVisible()
            or self._indicator_rect.isNull()
            or target.isNull()
        ):
            self._indicator_rect = target
            self.update()
            return

        self._indicator_animation.setStartValue(self._indicator_rect)
        self._indicator_animation.setEndValue(target)
        self._indicator_animation.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Tab geometry is final after the bar is shown, so paint the initial
        # underline at the active tab instead of animating from an empty rect.
        self._indicator_rect = self._target_indicator_rect(self.currentIndex())
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._indicator_animation.stop()
        self._indicator_rect = self._target_indicator_rect(self.currentIndex())
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        rect = self._indicator_rect
        if rect.width() <= 0 or rect.height() <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        gradient.setColorAt(0.0, QColor("#6572ff"))
        gradient.setColorAt(0.55, QColor("#8270ff"))
        gradient.setColorAt(1.0, QColor("#38cde1"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 1.5, 1.5)


class AnimatedStackedWidget(QStackedWidget):
    """A page stack with a brief snapshot cross-fade and low-distance slide."""

    TRANSITION_MS = 245
    SLIDE_DISTANCE = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_transition = None

    def setCurrentIndex(self, index: int) -> None:
        if index == self.currentIndex():
            return

        # Complete an interrupted transition before taking the next snapshot.
        self._finish_transition()

        old_index = self.currentIndex()
        old_page = self.currentWidget()
        can_animate = (
            animations_enabled()
            and self.isVisible()
            and old_page is not None
            and 0 <= index < self.count()
        )
        snapshot = None
        old_geometry = None
        if can_animate:
            try:
                old_geometry = old_page.geometry()
                snapshot = old_page.grab()
            except RuntimeError:
                snapshot = None

        super().setCurrentIndex(index)
        new_page = self.currentWidget()

        if (
            not can_animate
            or new_page is None
            or old_page is new_page
            or snapshot is None
            or snapshot.isNull()
        ):
            return

        target_pos = new_page.pos()
        direction = 1 if index > old_index else -1

        # The old page is a lightweight pixmap overlay; live page widgets remain
        # normally rendered underneath it throughout the transition.
        overlay = QLabel(self)
        overlay.setObjectName("page_transition_overlay")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        overlay.setStyleSheet("background: transparent; border: none; padding: 0;")
        overlay.setPixmap(snapshot)
        overlay.setGeometry(old_geometry or self.rect())

        overlay_effect = QGraphicsOpacityEffect(overlay)
        overlay_effect.setOpacity(1.0)
        overlay.setGraphicsEffect(overlay_effect)

        new_page.move(target_pos + QPoint(direction * self.SLIDE_DISTANCE, 0))
        new_page.show()
        overlay.show()
        overlay.raise_()

        group = QParallelAnimationGroup(self)
        fade = QPropertyAnimation(overlay_effect, b"opacity", group)
        fade.setDuration(self.TRANSITION_MS)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        outgoing = QPropertyAnimation(overlay, b"pos", group)
        outgoing.setDuration(self.TRANSITION_MS)
        outgoing.setStartValue(overlay.pos())
        outgoing.setEndValue(overlay.pos() - QPoint(direction * self.SLIDE_DISTANCE, 0))
        outgoing.setEasingCurve(QEasingCurve.Type.OutCubic)

        incoming = QPropertyAnimation(new_page, b"pos", group)
        incoming.setDuration(self.TRANSITION_MS)
        incoming.setStartValue(new_page.pos())
        incoming.setEndValue(target_pos)
        incoming.setEasingCurve(QEasingCurve.Type.OutCubic)

        transition = {
            "group": group,
            "overlay": overlay,
            "page": new_page,
            "target_pos": target_pos,
        }
        self._active_transition = transition
        group.finished.connect(
            lambda current=transition: self._complete_transition(current)
        )
        group.start()

    def resizeEvent(self, event) -> None:
        if self._active_transition is not None:
            self._finish_transition()
        super().resizeEvent(event)

    def _complete_transition(self, transition) -> None:
        if self._active_transition is not transition:
            return
        self._active_transition = None

        page = transition["page"]
        if self.indexOf(page) >= 0:
            page.move(transition["target_pos"])

        overlay = transition["overlay"]
        overlay.setGraphicsEffect(None)
        overlay.hide()
        overlay.deleteLater()
        transition["group"].deleteLater()

    def _finish_transition(self) -> None:
        transition = self._active_transition
        if transition is None:
            return
        self._active_transition = None

        group = transition["group"]
        group.stop()

        page = transition["page"]
        if self.indexOf(page) >= 0:
            page.move(transition["target_pos"])

        overlay = transition["overlay"]
        overlay.setGraphicsEffect(None)
        overlay.hide()
        overlay.deleteLater()
        group.deleteLater()


class ButtonHoverAnimations(QObject):
    """Adds a restrained animated glow on hover without changing button styles."""

    def __init__(self, root: QObject):
        super().__init__(root)
        self._root = root
        self._active = {}
        for button in root.findChildren(QPushButton):
            button.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if not isinstance(watched, QPushButton):
            return False
        if not self._root.isAncestorOf(watched):
            return False

        if event.type() == QEvent.Type.Enter:
            self._animate_hover(watched, True)
        elif event.type() == QEvent.Type.Leave:
            self._animate_hover(watched, False)
        return False

    def _animate_hover(self, button: QPushButton, hovered: bool) -> None:
        if not animations_enabled() or not button.isEnabled():
            return
        if button.width() < 34 or button.height() < 26:
            return
        if button.objectName() in {
            "window_minimize", "window_maximize", "window_close",
        }:
            return

        record = self._active.get(button)
        if record is None:
            if button.graphicsEffect() is not None:
                return
            effect = QGraphicsDropShadowEffect(button)
            effect.setOffset(0, 2)
            effect.setBlurRadius(0)
            effect.setColor(QColor(99, 91, 255, 0))
            button.setGraphicsEffect(effect)
        else:
            effect = record["effect"]
            record["group"].stop()
            record["group"].deleteLater()

        group = QParallelAnimationGroup(self)
        blur = QPropertyAnimation(effect, b"blurRadius", group)
        blur.setDuration(175)
        blur.setStartValue(effect.blurRadius())
        blur.setEndValue(12.0 if hovered else 0.0)
        blur.setEasingCurve(QEasingCurve.Type.OutCubic)

        color = QPropertyAnimation(effect, b"color", group)
        color.setDuration(175)
        color.setStartValue(effect.color())
        color.setEndValue(
            QColor(99, 91, 255, 85 if hovered else 0)
        )
        color.setEasingCurve(QEasingCurve.Type.OutCubic)

        record = {"effect": effect, "group": group}
        self._active[button] = record
        group.finished.connect(
            lambda target=button, current_effect=effect, current_group=group, active=hovered:
            self._finish_hover(target, current_effect, current_group, active)
        )
        group.start()

    def _finish_hover(self, button, effect, group, hovered: bool) -> None:
        record = self._active.get(button)
        if record is None or record["group"] is not group:
            return
        if not hovered:
            if button.graphicsEffect() is effect:
                button.setGraphicsEffect(None)
            self._active.pop(button, None)
        group.deleteLater()
