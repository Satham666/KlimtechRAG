# Dodaj to do ~/.config/fish/config.fish

# Alias do szybkiej synchronizacji git
function gitsync
    set commit_msg "Sync: "(date +%Y-%m-%d_%H:%M)
    if test (count $argv) -gt 0
        set commit_msg $argv[1]
    end
    
    echo "🔄 Git Full Sync"
    
    # Sprawdź czy są zmiany
    if test (git status --porcelain | wc -l) -gt 0
        echo "📝 Dodawanie zmian..."
        git add -A
        git commit -m $commit_msg
    end
    
    # Zawsze push (force)
    echo "📤 Wysyłanie na GitHub..."
    git push --force
    
    echo "✅ Gotowe!"
    git log -1 --oneline
end

# Alias do diagnostyki
function gitstatus
    echo "📊 Status synchronizacji:"
    git fetch
    echo ""
    echo "Niezacommitowane:"
    git status --short
    echo ""
    echo "Niewypushowane commity:"
    git log origin/main..HEAD --oneline
end
