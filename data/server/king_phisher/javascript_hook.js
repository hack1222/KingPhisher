/* http://stackoverflow.com/questions/950087 */
function loadScript(url, callback) {
  var head = document.getElementsByTagName('head')[0];
  var script = document.createElement('script');
  script.type = 'text/javascript';
  script.src = url;
  if (callback !== undefined) {
    script.onreadystatechange = callback;
    script.onload = callback;
  }
  head.appendChild(script);
}
