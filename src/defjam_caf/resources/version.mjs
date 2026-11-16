/** One player-facing version label for Home and both editors. */
export function workshopVersion(version = '') {
  return 'Fighter Workshop ' + version.replace(/^(\d+\.\d+)\.0(?=[ab]|rc|$)/, '$1')
    .replace(/a(\d+)$/, ' alpha $1').replace(/b(\d+)$/, ' beta $1').replace(/rc(\d+)$/, ' rc $1');
}
