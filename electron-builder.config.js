module.exports = {
  appId: 'com.creditnexus.app',
  productName: 'CreditNexus',
  directories: {
    output: 'dist-electron'
  },
  files: [
    'electron/**/*',
    'client/dist/**/*',
    'app/**/*',
    'server.py',
    'requirements.txt',
    'package.json',
    'alembic.ini',
    'alembic/**/*',
    '!**/__pycache__/**',
    '!**/*.pyc',
    '!**/node_modules/**',
    '!**/.git/**'
  ],
  win: {
    target: ['nsis', 'portable'],
    icon: 'assets/icon.ico'
  },
  mac: {
    target: ['dmg', 'zip'],
    icon: 'assets/icon.icns',
    category: 'public.app-category.finance'
  },
  linux: {
    target: ['AppImage', 'deb'],
    icon: 'assets/icon.png',
    category: 'Finance'
  },
  nsis: {
    oneClick: false,
    allowToChangeInstallationDirectory: true
  }
};
