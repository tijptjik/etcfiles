function setup_logging
    set tag $argv[1]

    if status is-interactive
        function log
            echo $argv
        end
    else
        function log --inherit-variable tag
            echo $argv | systemd-cat -t $tag
        end
    end
end
