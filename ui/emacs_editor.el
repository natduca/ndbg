;; Copyright 2011 Google Inc.
;;
;; Licensed under the Apache License, Version 2.0 (the "License");
;; you may not use this file except in compliance with the License.
;; You may obtain a copy of the License at
;;
;;      http://www.apache.org/licenses/LICENSE-2.0
;;
;; Unless required by applicable law or agreed to in writing, software
;; distributed under the License is distributed on an "AS IS" BASIS,
;; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
;; See the License for the specific language governing permissions and
;; limitations under the License.

;; helper code
(defun ndbg-get-line-start-pos (line)
  (line-beginning-position (1+ (- line (line-number-at-pos)))))
(defun make-marker-at-pos (pos)
  (set-marker (make-marker) pos))

;; image code


(defvar ndbg-currently-set-lines nil)
(make-variable-buffer-local 'ndbg-currently-set-lines)

(defun ndbg-ensure-buffer-initialized ()
  (unless ndbg-currently-set-lines
;;    (message (format "Initialized for %s" (current-buffer)))
    (setq ndbg-currently-set-lines (make-hash-table))
    )
  (dolist (w (get-buffer-window-list (current-buffer) nil t))
    (set-window-margins w 4 0)
    )
  )




(defun ndbg-set-image-at-line (img line)
  ;; set up this buffer if that hasn't happened yet
  (ndbg-ensure-buffer-initialized)
  (when (gethash line ndbg-currently-set-lines)
    (throw 'line-already-marked))
  (let* ((line-start-pos (ndbg-get-line-start-pos line))
         (m (make-marker-at-pos line-start-pos)))
;;    (message (format "ndbg-set-image-at-line %s %s" img line))
    (set-marker-insertion-type m nil) ;; keep the marker from moving during edits
    (put-image img m nil 'left-margin)
    (puthash  line m ndbg-currently-set-lines)))

(defun ndbg-remove-image-at-line (line)
  (ndbg-ensure-buffer-initialized)
  (unless (gethash line ndbg-currently-set-lines)
    (throw 'line-not-marked))
  (let* ((m (gethash line ndbg-currently-set-lines))
         (pos (marker-position m)))
    (remove-images pos pos)
    (remhash line ndbg-currently-set-lines)
    ))

;;; ndbg mode
(defun ndbg-after-scroll (win start)
;;  (message (format "%s: Checking %s" (selected-window) (current-buffer)))
  (ndbg-ensure-buffer-initialized))

(define-minor-mode ndbg-mode
  """Toggle ndbg features throughout emacs"""
  :lighter
  (if (and ndbg-mode (not (minibufferp)))
      (progn ;; true case --- add hooks
;;        (message (format "ndbg-mode on for %s" (current-buffer)))
        )
    (progn ;; else case --- remove everything
;;      (message (format "ndbg-mode off for %s" (current-buffer)))
      )))

;;(add-hook 'window-scroll-functions 'ndbg-after-scroll)
(add-hook 'window-configuration-change-hook 'ndbg-ensure-buffer-initialized)


(define-globalized-minor-mode global-ndbg-mode ndbg-mode ndbg-on)

;; called per-buffer to enable ndbg mode
(defun ndbg-on ()
  (unless (minibufferp)
    (ndbg-mode 't)))

(defun ndbg-set-current-line (file line)
  (with-current-buffer (find-file-noselect file)
    (beginning-of-buffer)
    (forward-line (- line 1))))


;; init the ndbg session
(global-linum-mode 0)
(linum-mode nil)
;;(setq linum-format "%5d ")
(global-ndbg-mode 't)
;;(message "initialized")
