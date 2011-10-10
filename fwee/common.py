def pad(lst, count, val=None):
	if count>len(lst):
		lst.extend([val for i in range(0, count-len(lst))])
	return lst