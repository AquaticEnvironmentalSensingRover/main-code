from pymongo.collection import Collection
import logging
import time
import datetime
import sys


class DataSource:
    ESCALATE_WAIT = 30

    def __init__(self, mongo_main: Collection, mongo_status: Collection, logger: logging.Logger, read_func, atype,
                 param_unit, itype=None, description=None, vertype=1.0):
        self.mongo_main = mongo_main
        self.mongo_status = mongo_status
        self.read_func = read_func
        self.param_unit = param_unit
        self.id = {'atype': atype, 'itype': itype}
        self.desc = description
        self.vertype = vertype
        self.logger = logger
        self.last_change = None

    def last_matching_status_data(self):
        db_col = self.mongo_status
        for ii in db_col.find().sort([['_id', 1]]):
            new_atype = ii.get('atype', None)
            new_itype = ii.get('itype', None)
            if (new_atype == self.id['atype']) and (new_itype == self.id['itype']):
                return ii
        return None

    def update_status_data(self, base, param):
        old_status_data = self.last_matching_status_data()
        new_status_data = dict(base)
        new_status_data['param'] = param
        if old_status_data is not None:
            self.mongo_status.update_one({'_id': old_status_data['_id']}, {'$set': new_status_data}, upsert=False)
        else:
            self.mongo_status.insert_one(new_status_data)

    def update_status(self, base_d, p):
        write_data = dict(base_d)
        write_data['vertype'] = 1.0
        self.update_status_data(write_data, p)

    def generate_log_with_name(self, start_text, state, trail_text=None):
        msg = start_text + " {}".format(self.id['atype'])
        if trail_text is not None:
            msg += " " + trail_text
        extra = {'atype': self.id['atype']}
        if self.id['itype'] is not None:
            msg += "-{}".format(self.id['itype'])
            extra['itype'] = self.id['itype']
        extra['state'] = state
        return {'msg': msg, 'extra': extra}

    def read_store(self):
        current_time = time.time()

        base_write_data = dict(self.id)
        base_write_data['ts'] = current_time
        base_write_data['tss'] = datetime.datetime.fromtimestamp(current_time).strftime('%b %d, %Y %H:%M.%S')

        try:
            # Write device read data to data collection
            param = self.read_func()
            write_data = dict(base_write_data)
            write_data['vertype'] = self.vertype
            write_data['param'] = param
            write_data['paramunit'] = self.param_unit
            write_data['desc'] = self.desc

            self.mongo_main.insert_one(write_data)
        except KeyboardInterrupt:
            raise
        except:
            self.logger.debug(**self.generate_log_with_name("Failed to communicate to ", False))
            if self.last_change is not None and not self.last_change['s']:
                if self.last_change['ts'] is not None and current_time-self.last_change['ts'] > self.ESCALATE_WAIT:
                    self.logger.exception(
                        **self.generate_log_with_name("Failed to communicate to ", False,
                                                      "for {} seconds".format(self.ESCALATE_WAIT)))
                    self.last_change['ts'] = None
            else:
                self.last_change = {'ts': current_time, 's': False}

            self.update_status_data(base_write_data, str(sys.exc_info()[1]))
        else:
            if self.last_change is not None and not self.last_change['s']:
                self.logger.log(logging.ERROR+1, **self.generate_log_with_name("Regained connection to ", True))
            self.last_change = {'ts': current_time, 's': True}
            # Update Status
            self.update_status_data(base_write_data, 'OK')

