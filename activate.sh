# UoM Lab Manager V2 - Activation Environment

# Load Zsh hook module safely
autoload -Uz add-zsh-hook

# Clear the last command variable
export LAB_LAST_CMD=""

# The tracking functions
lab_preexec() {
    export LAB_LAST_CMD="$1"
}

lab_precmd() {
    local exit_code=$?
    # Do not log empty commands, the 'ai' commands, or the deactivate command
    if [[ -n "$LAB_LAST_CMD" && "$LAB_LAST_CMD" != "ai "* && "$LAB_LAST_CMD" != "deactivate_lab" ]]; then
        # NOTE: Pointing to v2 folder!
        python3 ~/.lab_manager_v2/manager.py log "$LAB_LAST_CMD" "$exit_code"
    fi
    export LAB_LAST_CMD=""
}

# Turn the hooks on
add-zsh-hook preexec lab_preexec
add-zsh-hook precmd lab_precmd

# Add the manual AI query shortcut (Pointing to v2 folder!)
alias ai="noglob python3 ~/.lab_manager_v2/manager.py ask"

# Create a command to easily turn it off
deactivate_lab() {
    add-zsh-hook -d preexec lab_preexec
    add-zsh-hook -d precmd lab_precmd
    unalias ai
    unset LAB_LAST_CMD
    echo "🛑 UoM Lab Manager V2 Deactivated. Terminal returning to normal."
}

# When activated, immediately trigger the Session Menu!
python3 ~/.lab_manager_v2/manager.py init
