tell application "Google Chrome"
    activate
    set tabCount to count of tabs of window 1
    log "Found " & tabCount & " tabs"
    
    repeat with i from 1 to tabCount
        tell window 1
            set active tab index of window 1 to i
            delay 0.5
            
            -- 执行JavaScript点击保存按钮
            set saveResult to execute tab i javascript "
                (function() {
                    // 查找保存按钮
                    var selectors = [
                        'a:has-text(\"保存到我的网盘\")',
                        '[node-type=\"bottomShareSave\"]',
                        'a[class*=\"save\"]',
                        '.save-btn',
                        'a:has-text(\"保存\")'
                    ];
                    
                    for (var i = 0; i < selectors.length; i++) {
                        var elements = document.querySelectorAll(selectors[i]);
                        for (var j = 0; j < elements.length; j++) {
                            if (elements[j].offsetWidth > 0 && elements[j].offsetHeight > 0) {
                                elements[j].click();
                                return 'clicked';
                            }
                        }
                    }
                    return 'not found';
                })();
            "
            
            log "Tab " & i & ": " & saveResult
            
            -- 等待保存对话框
            delay 2
            
            -- 尝试确认保存（如果有确认对话框）
            try
                execute tab i javascript "
                    (function() {
                        // 查找确认按钮
                        var confirmBtns = document.querySelectorAll('[node-type=\"savePathConfirm\"], .save-btn-confirm, button:has-text(\"确定\")');
                        for (var i = 0; i < confirmBtns.length; i++) {
                            if (confirmBtns[i].offsetWidth > 0) {
                                confirmBtns[i].click();
                                return 'confirmed';
                            }
                        }
                        return 'no confirm';
                    })();
                "
            end try
            
            delay 1.5
        end tell
    end repeat
end tell

return "✅ 完成！已处理所有标签页"
