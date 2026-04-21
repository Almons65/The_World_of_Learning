from PySide6.QtWidgets import QLayout
from PySide6.QtCore import Qt, QRect, QSize, QPoint

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, hSpacing=18, vSpacing=18):
        super().__init__(parent)
        self.m_hSpace = hSpacing
        self.m_vSpace = vSpacing
        self.itemList = []
        if margin != -1:
            self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def doLayout(self, rect, testOnly):
        m = self.contentsMargins()
        effectiveRect = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())

        if not self.itemList:
            return 0

        wid0 = self.itemList[0].widget()
        base_w = getattr(wid0, 'base_width', 460) if wid0 else 460
        base_h = getattr(wid0, 'base_height', 340) if wid0 else 340
        aspect = base_h / base_w

        spaceX = self.m_hSpace
        spaceY = self.m_vSpace
        avail_w = effectiveRect.width()

        # Determine number of columns based on base width
        cols = max(1, (avail_w + spaceX) // (base_w + spaceX))
        cols = min(cols, len(self.itemList))

        # Stretch cards to fill the full available width — no gaps on sides
        stretched_w = (avail_w - (cols - 1) * spaceX) // cols
        stretched_h = int(stretched_w * aspect)

        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0
        col_idx = 0

        for item in self.itemList:
            wid = item.widget()
            size = QSize(stretched_w, stretched_h)

            if col_idx >= cols and col_idx > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                lineHeight = 0
                col_idx = 0

            if not testOnly:
                if wid:
                    wid.setFixedSize(stretched_w, stretched_h)
                item.setGeometry(QRect(QPoint(x, y), size))

            x += stretched_w + spaceX
            lineHeight = max(lineHeight, stretched_h)
            col_idx += 1

        return y + lineHeight - rect.y() + m.bottom()
