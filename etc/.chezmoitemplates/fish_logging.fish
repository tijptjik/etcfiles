function setup_logging
    set -g chezetc_log_tag $argv[1]

    function _chezetc_system_log
        if command -q systemd-cat
            echo $argv | systemd-cat -t $chezetc_log_tag
        end
    end

    function _chezetc_style
        set color $argv[1]
        set -e argv[1]

        if command -q gum; and isatty stdout
            gum style --foreground "$color" --bold $argv
        else
            echo $argv
        end
    end

    function _chezetc_emit
        echo $argv
        _chezetc_system_log $argv
    end

    function step_header
        set title $argv
        if command -q gum; and isatty stdout
            gum style --foreground 39 --bold "==> $title"
        else
            echo "==> $title"
        end
        _chezetc_system_log "START $title"
    end

    function step_ok
        set title $argv
        _chezetc_style 42 "OK   $title"
        _chezetc_system_log "OK $title"
    end

    function step_skip
        set title $argv
        _chezetc_style 244 "SKIP $title"
        _chezetc_system_log "SKIP $title"
    end

    function step_fail
        set title $argv
        _chezetc_style 196 "FAIL $title"
        _chezetc_system_log "FAIL $title"
    end

    function step_note
        set message $argv
        _chezetc_emit "NOTE $message"
    end

    function step_run
        set title $argv[1]
        set cmd $argv[2..]

        if test (count $cmd) -eq 0
            step_fail "$title"
            return 1
        end

        _chezetc_system_log "RUN $title: $cmd"

        if command -q gum; and isatty stdout
            gum spin --show-error --title "$title" -- $cmd
        else
            echo "RUN  $title"
            $cmd
        end

        set run_status $status
        if test $run_status -eq 0
            step_ok "$title"
        else
            step_fail "$title"
        end

        return $run_status
    end

    function log
        _chezetc_system_log $argv
    end
end
