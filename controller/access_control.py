import logging
CUR_ALLOWED = set()

def logger():
    return logging.getLogger('access_control')

def authorize(mac):
    if mac in CUR_ALLOWED:
        logger().error('Attempted to add {0!r} twice'.format(mac))
    else:
        CUR_ALLOWED.add(mac)
        logger().info('Authorized {0!r}'.format(mac))

def revoke(mac):
    if mac not in CUR_ALLOWED:
        logger().error('Attempted to remove {0!r} twice'.format(mac))
    else:
        CUR_ALLOWED.remove(mac)
        logger().info('Revoked {0!r}'.format(mac))
