# Included by the pre- and post-update hooks on the WebDAV server.  Fedora's
# nginx-mod-devel package contains the exact Nginx source tree and RPM macros
# that match the installed Nginx ABI, so do not replace this with an upstream
# Nginx source tarball.

set -g nginx_dav_ext_version 3.0.0
set -g nginx_dav_ext_release 3
set -g nginx_dav_ext_checksum d2499d94d82d4e4eac8425d799e52883131ae86a956524040ff2fd230ef9f859
set -g nginx_dav_ext_source_url "https://github.com/arut/nginx-dav-ext-module/archive/refs/tags/v$nginx_dav_ext_version.tar.gz"
set -g nginx_dav_ext_root /var/cache/chezetc/nginx-mod-dav-ext

function nginx_dav_ext_current_abi
    rpm -q --qf '%{VERSION}' nginx 2>/dev/null
end

function nginx_dav_ext_is_current
    set -l nginx_abi (nginx_dav_ext_current_abi)
    test -n "$nginx_abi"
    and rpm -q --whatprovides "nginx-mod-dav-ext(nginx-abi) = $nginx_abi" >/dev/null 2>&1
end

function write_nginx_dav_ext_spec
    set -l spec_file $argv[1]
    set -l nginx_abi (nginx_dav_ext_current_abi)
    test -n "$nginx_abi"
    or return 1

    begin
        echo 'Name:           nginx-mod-dav-ext'
        echo 'Version:        3.0.0'
        echo "Release:        $nginx_dav_ext_release%{?dist}.nginx$nginx_abi"
        echo 'Summary:        Extended WebDAV module for Nginx'
        echo
        echo 'License:        BSD-2-Clause'
        echo 'URL:            https://github.com/arut/nginx-dav-ext-module'
        echo 'Source0:        nginx-dav-ext-module-%{version}.tar.gz'
        echo
        echo 'BuildRequires:  nginx-mod-devel'
        echo 'Requires:       nginx'
        echo 'Requires:       libxml2'
        echo 'Requires:       libxslt'
        echo '# Rebuild after DNF updates instead of preventing Nginx updates.'
        echo '%global __requires_exclude_from ^%{nginx_moddir}/.*\\.so$'
        echo "Provides:       nginx-mod-dav-ext(nginx-abi) = $nginx_abi"
        echo
        echo '%description'
        echo 'Dynamic Nginx module that adds WebDAV PROPFIND, OPTIONS, LOCK, and'
        echo 'UNLOCK support to the standard ngx_http_dav_module.'
        echo
        echo '%prep'
        echo '%autosetup -n nginx-dav-ext-module-%{version}'
        echo
        echo '%build'
        echo '%nginx_modconfigure --with-http_dav_module --with-http_xslt_module=dynamic'
        echo '%nginx_modbuild'
        echo
        echo '%install'
        echo 'pushd %{_vpath_builddir}'
        echo 'install -dm 0755 %{buildroot}%{nginx_moddir}'
        echo 'install -pm 0755 ngx_http_dav_ext_module.so %{buildroot}%{nginx_moddir}'
        echo 'popd'
        echo
        echo 'install -dm 0755 %{buildroot}%{nginx_modconfdir}'
        echo "echo 'load_module \"%{nginx_moddir}/ngx_http_dav_ext_module.so\";' > %{buildroot}%{nginx_modconfdir}/mod-dav-ext.conf"
        echo
        echo '%files'
        echo '%license LICENSE'
        echo '%doc README.rst'
        echo '%{nginx_moddir}/ngx_http_dav_ext_module.so'
        echo '%{nginx_modconfdir}/mod-dav-ext.conf'
    end | sudo tee "$spec_file" >/dev/null
end

function ensure_nginx_dav_ext
    if nginx_dav_ext_is_current
        step_skip_ok "Nginx DAV extension" current
        return 0
    end

    # This migration removes the subscription-gated repository package.  Its
    # Nginx build is replaced with the Fedora build before the local module is
    # compiled, ensuring the module and daemon always share an ABI.
    if rpm -q getpagespeed-extras-release >/dev/null 2>&1
        step_run "Remove GetPageSpeed repository" sudo dnf remove -y getpagespeed-extras-release
        or return 1
    end

    # The old repository module requires the GetPageSpeed-specific nginx-r
    # capability. Remove it before switching back to Fedora Nginx; the
    # currently running daemon keeps serving until the local replacement is
    # installed, validated, and reloaded below.
    if rpm -q nginx-module-dav-ext >/dev/null 2>&1
        step_run "Remove GetPageSpeed DAV extension" sudo dnf remove -y nginx-module-dav-ext
        or return 1
    end

    # DNF5's distro-sync only accepts installed packages. Sync the existing
    # GetPageSpeed nginx package first; Fedora's split subpackages are added
    # by the following install transaction.
    step_run "Sync Fedora Nginx" sudo dnf distro-sync -y --allowerasing nginx
    or return 1
    step_run "Nginx runtime and module build dependencies" sudo dnf install -y nginx-core nginx-mod-stream nginx-mod-devel rpm-build
    or return 1

    if nginx_dav_ext_is_current
        step_skip_ok "Nginx DAV extension" current
        return 0
    end

    set -l source_dir "$nginx_dav_ext_root/SOURCES"
    set -l spec_dir "$nginx_dav_ext_root/SPECS"
    set -l rpm_dir "$nginx_dav_ext_root/RPMS"
    set -l source_archive "$source_dir/nginx-dav-ext-module-$nginx_dav_ext_version.tar.gz"
    set -l spec_file "$spec_dir/nginx-mod-dav-ext.spec"

    step_run "Prepare Nginx DAV RPM workspace" sudo install -d -m 0755 "$source_dir" "$spec_dir" "$rpm_dir"
    or return 1

    set -l source_is_valid false
    if test -f "$source_archive"
        echo "$nginx_dav_ext_checksum  $source_archive" | sudo sha256sum --check --status
        and set source_is_valid true
    end

    if not $source_is_valid
        set -l downloaded_source (mktemp)
        or return 1
        step_run "Download Nginx DAV source" curl --fail --location --silent --show-error --max-time 60 --output "$downloaded_source" "$nginx_dav_ext_source_url"
        or begin
            rm -f "$downloaded_source"
            return 1
        end
        echo "$nginx_dav_ext_checksum  $downloaded_source" | sha256sum --check --status
        or begin
            rm -f "$downloaded_source"
            step_warn "Nginx DAV source checksum mismatch"
            return 1
        end
        sudo install -m 0644 "$downloaded_source" "$source_archive"
        and rm -f "$downloaded_source"
        or return 1
    end

    write_nginx_dav_ext_spec "$spec_file"
    or return 1

    # Keep discovery deterministic across Nginx ABI rebuilds. RPM may choose
    # an architecture-specific output directory, so do not infer that path.
    step_run "Clear previous Nginx DAV RPM" sudo find "$rpm_dir" -type f -name 'nginx-mod-dav-ext-*.rpm' -delete
    or return 1
    step_run "Build Nginx DAV RPM" sudo rpmbuild -bb --define "_topdir $nginx_dav_ext_root" "$spec_file"
    or return 1

    set -l built_rpm
    for candidate in (find "$rpm_dir" -type f -name 'nginx-mod-dav-ext-*.rpm')
        if test (rpm -qp --qf '%{NAME}' "$candidate" 2>/dev/null) = nginx-mod-dav-ext
            set built_rpm "$candidate"
            break
        end
    end
    if test -z "$built_rpm"
        step_warn "Nginx DAV RPM was not produced"
        return 1
    end

    step_run "Install Nginx DAV extension" sudo dnf install -y "$built_rpm"
    or return 1
    step_run "Validate Nginx configuration" sudo nginx -t
    or return 1
    step_run "Reload Nginx" sudo systemctl reload nginx
end
