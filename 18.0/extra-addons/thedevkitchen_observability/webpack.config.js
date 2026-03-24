const path = require('path');

module.exports = {
  entry: './static/src/js/browser_tracer.js',
  output: {
    filename: 'opentelemetry-bundle.js',
    path: path.resolve(__dirname, 'static/lib'),
    library: {
      name: 'OdooOTel',
      type: 'umd',
      export: 'default',
    },
  },
  mode: 'production',
  devtool: 'source-map',
  resolve: {
    extensions: ['.js'],
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
      },
    ],
  },
  optimization: {
    minimize: true,
  },
};
