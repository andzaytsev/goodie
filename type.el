;(setq auto-save-timeout 1)
;(setq auto-save-interval 1)

; Unique process id for each invocation of the script
(setq process-counter 0)
; Flag to indicate if file should be compiled
(setq hack-compile-flag 0)
; Flag to indicate if line numbers should be included
(setq hack-add-line-numbers-flag 0)
; Flag to indicate if code quality should be checked
(setq hack-check-code-quality-flag 0)

(defun full-auto-save (editing-buffer-name)
  (save-excursion
    (dolist (buf (buffer-list))
      (set-buffer buf)
      (if (and (buffer-file-name) (buffer-modified-p))
          (basic-save-buffer))))
  (setq process-counter (+ process-counter 1))
  (start-process-shell-command
   "hack-loop-process"
   "hack-buffer"
   (format "./main.py --single --id %s --file-name %s --compile %s --add-line-numbers %s --check-code-quality %s"
           (number-to-string process-counter)
           editing-buffer-name
           hack-compile-flag
           hack-add-line-numbers-flag
           hack-check-code-quality-flag)))

;(add-hook 'auto-save-hook 'full-auto-save)


(defun hack-begin ()
  (interactive)
  ;(start-process-shell-command "hack-loop-process" "hack-buffer" "./main.py")
  (call-process "/bin/bash" nil "hack-buffer" nil "-c" (format "./main.py --single --clean --file-name %s" (buffer-name)))
  (run-at-time "0 sec" 0.2 'full-auto-save (buffer-name)))


(defun hack-end ()
  (interactive)
  (cancel-function-timers 'full-auto-save))
;  (kill-process "hack-loop-process" nil))


(defun hack-on-compile ()
  (interactive)
  (setq hack-compile-flag 1))

(defun hack-off-compile ()
  (interactive)
  (setq hack-compile-flag 0))

(defun hack-on-line-numbers ()
  (interactive)
  (setq hack-add-line-numbers-flag 1))

(defun hack-off-line-numbers ()
  (interactive)
  (setq hack-add-line-numbers-flag 0))

(defun hack-on-code-quality ()
  (interactive)
  (setq hack-check-code-quality-flag 1))

(defun hack-off-code-quality ()
  (interactive)
  (setq hack-check-code-quality-flag 0))

