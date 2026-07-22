function setup_logging
    set -g chezetc_log_tag $argv[1]
    set -g chezetc_stage INSTALL

    switch $chezetc_log_tag
        case linux-dnf-update
            set chezetc_stage SYNC
        case linux-enable-docker linux-enable-sshd
            set chezetc_stage CONFIG
    end

    function _chezetc_system_log
        if command -q systemd-cat
            echo $argv | systemd-cat -t $chezetc_log_tag 2>/dev/null
        end
    end

    function _chezetc_emit
        echo $argv
        _chezetc_system_log $argv
    end

    function step_header
        set title $argv
        echo
        if command -q gum; and isatty stdout
            gum style --foreground 14 --bold "$title"
        else
            echo "$title"
        end
        echo
        _chezetc_system_log "START $title"
    end

    function step_ok
        set title $argv
        __stage_result "$chezetc_stage" "$title"
        _chezetc_system_log "OK $title"
    end

    function step_skip
        set title $argv
        __stage_label SKIP "-" "$title"
        _chezetc_system_log "SKIP $title"
    end

    function step_fail
        set title $argv
        __stage_failure "$title"
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
            gum spin --show-error --title (__stage_spin_title "$chezetc_stage" "$title") -- $cmd
        else
            __stage_label "$chezetc_stage" "..." "$title"
            $cmd
        end

        set run_status $status
        if test $run_status -eq 0
            __stage_result "$chezetc_stage" "$title"
        else
            __stage_failure "$title"
        end

        return $run_status
    end

    function step_run_as
        set stage_name $argv[1]
        set title $argv[2]
        set command $argv[3..]
        set previous_stage $chezetc_stage
        set chezetc_stage $stage_name
        step_run "$title" $command
        set run_status $status
        set chezetc_stage $previous_stage
        return $run_status
    end

    function log
        _chezetc_system_log $argv
    end
end
