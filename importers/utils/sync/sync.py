"""
sync is a function library for merging seed data into the database configured for the web application.

This is used for deploying imported data to app.accesslocator.com or demo.accesslocator.com.
"""
import MySQLdb
from import_helpers.seed_io import load_seed_data_from
import import_helpers.utils as utils
import db_config
import uuid
import json


def get_db_connection():
	connection_settings = db_config.get_connection_settings()
	db = MySQLdb.connect(host=connection_settings['DB_HOST'],
                     user=connection_settings['DB_USERNAME'],
                     passwd=connection_settings['DB_PASSWORD'],
                     db=connection_settings['DB_DATABASE'],
					 use_unicode=True, charset="utf8")
	return db


def is_matching_location(location1, location2):
	if 'id' in location1 and 'id' in location2:
		return location1['id'] == location2['id']

	return (
		location1['latitude'] == location2['latitude'] and
		location1['longitude'] == location2['longitude']
		)


def is_matching_user(user1, user2):
	return user1['email'] == user2['email']


def is_matching_id(e1, e2):
	return e1['id'] == e2['id']


def find_match(table_name, data_list, element):
	if table_name == 'location':
		match_func = is_matching_location
	elif table_name == 'user':
		match_func = is_matching_user
	else:
		match_func = is_matching_id

	matches = [e for e in data_list if match_func(e, element)]
	if len(matches) > 1:
		raise ValueError('More than 1 match found. match count = ' + str(len(matches)))
	elif len(matches) == 1:
		return matches[0]
	else:
		return None


def run_query(db, sql):
	cur = db.cursor(MySQLdb.cursors.DictCursor)
	cur.execute(sql)
	db_data = [row for row in cur.fetchall()]
	return db_data


def get_base_insert_sql(table_name, new_record_data):
	base_insert_sql = 'insert into `' + table_name + '`('
	for field_name in new_record_data.keys():
		base_insert_sql += '`' + field_name + '`,'

	base_insert_sql = base_insert_sql[:-1] + ') values(' # remove trailing comma.
	return base_insert_sql


def insert(cursor, table_name, new_row):
	values = []
	insert_sql = get_base_insert_sql(table_name, new_row)
	for field_name in new_row.keys():
		values.append(new_row[field_name])
		insert_sql += '%s,'

	insert_sql = insert_sql[:-1] + ')' # remove trailing comma.
	print 'Table ' + table_name + ' Inserting ' + str(new_row['id'])
	print 'SQL: ' + insert_sql
	print 'values: ' + str(values)
	cursor.execute(insert_sql, values)


def replace_all_data(db, table_names):
	cursor = db.cursor()
	for table_name in table_names:
		run_query(db, 'delete from `' + table_name + '`')
		table_data = load_seed_data_from(table_name)
		for table_record_data in table_data:
			insert(cursor, table_name, table_record_data)

	db.commit()


def get_hash_string(values):
	result = ''
	for val in values:
		result += str(val) + '-'
	if result != '':
		result = result[:-1]
	return result


def filter_keys(dict1, keys):
	result = {}
	for key in keys:
		result[key] = dict1[key]
	return result


def add_missing_data_with_composite_keys(db, cursor, table_name, composite_keys):
	json_data = load_seed_data_from(table_name)
	sql = 'select '
	for key in composite_keys:
		sql += '`' + key + '`,'
	sql = sql[:-1] + ' from `' + table_name + '`'
	db_data = run_query(db, sql)
	db_data = [get_hash_string(row.values()) for row in db_data]
	db_data = set(db_data) # The "in" operator works more efficiently on sets.
	new_data = [new_row for new_row in json_data if get_hash_string(filter_keys(new_row, composite_keys).values()) not in db_data]
	for new_row in new_data:
		insert(cursor, table_name, new_row)


def add_missing_data(db, table_names):
	cursor = db.cursor()
	for table_name in table_names:
		if isinstance(table_name, dict):
			add_missing_data_with_composite_keys(db, cursor, table_name['name'], table_name['composite_keys'])
		else:
			json_data = load_seed_data_from(table_name)
			db_data = run_query(db, 'select id from ' + table_name)
			db_data = [row['id'] for row in db_data]
			db_data = set(db_data) # The "in" operator works more efficiently on sets.
			new_data = [new_row for new_row in json_data if new_row['id'] not in db_data]
			for new_row in new_data:
				insert(cursor, table_name, new_row)
	db.commit()


def offset_question_order(db):
	cursor = db.cursor()
	cursor.execute('update question set `order`=`order` + 100')


def set_fields_on_questions(db):
	cursor = db.cursor()
	questions_data = load_seed_data_from('question')
	# Update order to prevent unique constraint violations 
	# as order is updated in the following loop.
	cursor = db.cursor()
	for question_data in questions_data:
		update_sql = 'update question set question_html=%s, is_always_required=%s, `order`=%s, explanation=%s, is_required_config=%s, name=%s where id=%s'
		cursor.execute(update_sql, (question_data['question_html'],
			question_data['is_always_required'], question_data['order'], question_data['explanation'], question_data['is_required_config'], question_data['name'], question_data['id']))

def set_fields_on_location_tags(db):
	print 'setting fields on location_tags table'
	location_tags_data = load_seed_data_from('location_tag')
	cursor = db.cursor()
	for location_tag in location_tags_data:
		update_sql = 'update location_tag set description=%s, icon_selector=%s where id=%s'
		cursor.execute(update_sql, (location_tag['description'], location_tag['icon_selector'], location_tag['id']))


def update_coordinates_for_locations(db):
	location_ids = ['00000000-0000-0000-0000-000000000020']
	locations_data = load_seed_data_from('location')
	cursor = db.cursor(MySQLdb.cursors.DictCursor)
	for location_id in location_ids:
		matching_location = [loc for loc in locations_data if loc['id'] == location_id][0]
		location_statement = ('update location set latitude=%s,longitude=%s where id=\'%s\'' % 
			(matching_location['latitude'], matching_location['longitude'], location_id))
		cursor.execute(location_statement)
	db.commit()


def clear_ratings_cache(db):
	cur = db.cursor(MySQLdb.cursors.DictCursor)
	clear_cache_statement = 'update location set ratings_cache=null, universal_rating=null'
	cur.execute(clear_cache_statement)


def nullify_ratings_cache_when_missing_questions(db):
	"""
	Sets ratings_cache to null when not all questions are specified in the ratings_cache value.
	This is a little sanitization of the database.
	
	Aspects of the rating calculation in the web application assume that if ratings_cache is not null,
	it must set values for every question.
	"""
	questions = load_seed_data_from('question')
	questions = [q['id'] for q in questions]
	locations_with_ratings_cache = run_query(db, 'select id, ratings_cache from location where ratings_cache is not null')
	location_ids_to_clear = []
	for location in locations_with_ratings_cache:
		ratings = json.loads(location['ratings_cache'])
		for question_id in questions:
			if question_id not in ratings:
				location_ids_to_clear.append(location['id'])
				break
	if len(location_ids_to_clear) > 0:
		print('Clearing ratings_cache for %d locations.' % len(location_ids_to_clear))
		group_size = 100
		cursor = db.cursor()
		# Loop through groups.
		# We don't want to delete all at once because there may be a limit to the SQL query size.
		while (len(location_ids_to_clear) > 0):
			group_ids = location_ids_to_clear[0 : group_size]
			s = str(group_ids).replace('[', '(').replace(']', ')').replace('u', '')
			s = 'update location set ratings_cache=NULL where id in ' + s
			run_query(db, s)
			# Remove the elements that were already updated.
			location_ids_to_clear = location_ids_to_clear[len(group_ids):]
		db.commit()


def set_fields_on_locations(db):
	locations_data = load_seed_data_from('location')
	for location in locations_data:
		if location['external_web_url'] and len(location['external_web_url'])> 255:
			print 'external_web_url for location ' + str(location['id']) + ' is too long at ' + str(len(location['external_web_url'])) + '.'
			return

	# We're only concerned with locations that have either address, phone number, external_web_url, location_group_id or any combination so 
	# let's filter out the useless data.
	# This may boost efficiency of the m*n time loop below by reducing m considerably.
	locations_data = [location for location in locations_data if location['address'] or location['phone_number'] or location['external_web_url'] or location['location_group_id']]

	fields = ['address', 'phone_number', 'external_web_url', 'location_group_id', 'destroy_location_event_id']
	location_query = 'select * from location where 0'
	for field in fields:
		location_query += ' or %s is null or %s=\'\'' % (field, field)

	cur = db.cursor(MySQLdb.cursors.DictCursor)
	cur.execute(location_query)
	db_data = [row for row in cur.fetchall()]

	locations_data = utils.list_to_dict(locations_data)
	print 'May update up to ' + str(len(db_data)) + ' records'
	cursor = db.cursor()
	for db_location in db_data:
		location = None
		if db_location['id'] in locations_data:
			location = locations_data[db_location['id']]
		if location:
			fields_to_set = []
			field_values = []
			for field in fields:
				if location[field] and not db_location[field]:
					fields_to_set.append(field)
					field_values.append(location[field])

			if len(field_values) > 0:
				update_sql = 'update location set '
				for field in fields_to_set:
					update_sql += field + '=%s,'
				
				update_sql = update_sql[:-1] # remove trailing comma.
				update_sql += ' where id=\'' + str(location['id']) + '\''
				print 'running: ' + update_sql
				cursor.execute(update_sql, field_values)
	db.commit()


def safely_remove_removed_locations(db):
	locations_data = load_seed_data_from('location')
	json_location_ids = [loc['id'] for loc in locations_data]
	locations_with_answers = run_query(db, 
		'select distinct location_id from user_answer union distinct select distinct location_id from review_comment')
	locations_with_answers = [loc['location_id'] for loc in locations_with_answers]
	locations_in_db = run_query(db, 'select id from location where creator_user_id is null')
	
	# Convert list to set for more efficiency.
	locations_with_answers = set(locations_with_answers) 
	json_location_ids = set(json_location_ids)
	locations_safe_to_delete = [loc['id'] for loc in locations_in_db if loc['id'] not in locations_with_answers]
	locations_to_delete = [id for id in locations_safe_to_delete if id not in json_location_ids]
	if len(locations_to_delete) > 0:
		id_list = '('
		for location_id in locations_to_delete:
			id_list += '%s, '

		id_list = id_list[:-2] # remove trailing comma.
		id_list += ')'

		delete_location_location_tag_sql = 'delete from location_location_tag where location_id in ' + id_list
		stringified_ids = [str(id) for id in locations_to_delete]
		print 'removing locations: ' + (', '.join(stringified_ids))
		cursor = db.cursor()
		cursor.execute(delete_location_location_tag_sql, locations_to_delete)
		delete_location_sql = 'delete from location where id in ' + id_list
		cursor.execute(delete_location_sql, locations_to_delete)
		db.commit()


def add_locations_not_conflicting_with_user_added_locations(db):
	locations_data = load_seed_data_from('location')
	location_location_tags = load_seed_data_from('location_location_tag')
	json_location_ids = [loc['id'] for loc in locations_data]
	locations_in_db = run_query(db, 'select id from location')
	locations_in_db = [loc['id'] for loc in locations_in_db]
	# Convert list to set for more efficiency.
	locations_in_db = set(locations_in_db)
	locations_to_add = [id for id in json_location_ids if id not in locations_in_db]
	if len(locations_to_add) > 0:
		cursor = db.cursor()
		insert_sql = 'insert into location('
		for field in locations_data[0].keys():
			insert_sql += '`' + field + '`,'
		insert_sql = insert_sql[:-1] + ') values('
		for field in locations_data[0].keys():
			insert_sql += '%s,'
		insert_sql = insert_sql[:-1] + ')'
		location_tag_insert_sql = 'insert into location_location_tag(id, location_id, location_tag_id) values(%s, %s, %s)'
		for location in locations_to_add:
			print 'Adding location ' + str(location)
			# find location by id.
			location = [loc for loc in locations_data if loc['id'] == location][0]
			cursor.execute(insert_sql, location.values())
			location_tags = [loct for loct in location_location_tags if loct['location_id'] == location['id']]
			for location_tag in location_tags:
				new_guid = str(uuid.uuid4())
				cursor.execute(location_tag_insert_sql, (new_guid, location_tag['location_id'], location_tag['location_tag_id']))
		db.commit()


def add_missing_users(db):
	add_missing_data(db, ['user'])
	# May want to include user_role eventually.


if __name__ == 'main':
	set_fields_on_locations(get_db_connection())
