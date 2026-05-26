# Maintainer: Ammar Rexhaj <ammarrexhaj@gmail.com>
pkgname=controller-manager
pkgver=0.1.0
pkgrel=1
pkgdesc="GUI for viewing connected game controllers and testing inputs on Linux"
arch=('any')
url="https://github.com/YOUR_USERNAME/controller-manager"
license=('MIT')
depends=(
    'python>=3.10'
    'python-pyqt6'
    'python-evdev'
    'python-pyudev'
)
makedepends=('git')
source=("$pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')

package() {
    cd "$srcdir/$pkgname-$pkgver"

    # Install application files
    install -d "$pkgdir/usr/share/$pkgname"
    install -m644 main.py backend.py widgets.py tester.py window.py \
        "$pkgdir/usr/share/$pkgname/"

    # Launcher script
    install -d "$pkgdir/usr/bin"
    cat > "$pkgdir/usr/bin/$pkgname" <<EOF
#!/bin/sh
exec python /usr/share/$pkgname/main.py "\$@"
EOF
    chmod 755 "$pkgdir/usr/bin/$pkgname"

    # Desktop entry
    install -Dm644 "$pkgname.desktop" \
        "$pkgdir/usr/share/applications/$pkgname.desktop"

    # License + README
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
