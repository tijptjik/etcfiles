# Capture only the selected package versions. Package-manager dependencies are
# intentionally absent from these snapshots and therefore from the report.
function snapshot_rpm_versions
    set output_file $argv[1]
    set packages $argv[2..]

    begin
        set seen_packages
        for package in $packages
            if contains -- "$package" $seen_packages
                continue
            end
            set -a seen_packages "$package"

            set versions (rpm -q --qf '%{VERSION}\n' "$package" 2>/dev/null)
            if test (count $versions) -gt 0
                printf "%s\t%s\n" "$package" "$versions[1]"
            end
        end
    end >$output_file
end

function snapshot_flatpak_versions
    set output_file $argv[1]
    set packages $argv[2..]

    if test (count $packages) -eq 0
        command touch "$output_file"
        return 0
    end

    begin
        for installed in (flatpak list --system --app --columns=application,version 2>/dev/null)
            set fields (string split \t -- "$installed")
            if test (count $fields) -ge 2; and contains -- "$fields[1]" $packages
                printf "%s\t%s\n" "$fields[1]" "$fields[2]"
            end
        end
    end >$output_file
end

function report_package_updates
    set before_file $argv[1]
    set after_file $argv[2]

    for updated in (command cat "$after_file")
        set updated_fields (string split \t -- "$updated")
        if test (count $updated_fields) -lt 2
            continue
        end

        set package $updated_fields[1]
        set new_version $updated_fields[2]
        set old_version

        for installed in (command cat "$before_file")
            set installed_fields (string split \t -- "$installed")
            if test (count $installed_fields) -ge 2; and test "$installed_fields[1]" = "$package"
                set old_version $installed_fields[2]
                break
            end
        end

        if test -n "$old_version"; and test "$old_version" != "$new_version"
            __stage_label_note UPDATE "✓" "$package ($old_version)" "$new_version"
        end
    end
end
