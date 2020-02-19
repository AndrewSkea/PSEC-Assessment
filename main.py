import pandas
import numpy
import sys
import os
import time
import matplotlib
import math
from person import Person
from util import print_step, Func


class User(Person):
    def __init__(self, name, benefit_risk, seen_like):
        self.benefit_risk = benefit_risk
        self.seen_like = seen_like
        self.messages = []
        self.friends = []
        super(User, self).__init__(name)

    def __str__(self):
        return "User. {}, BvR: {}, SvL: {}".format(self.name, self.benefit_risk, self.seen_like)

    def set_messages(self, msgs):
        self.messages = msgs

    def set_friends(self, friends):
        self.friends = friends

    # Helper Functions
    def increase_seen_for_friends(self):
        [friend.num_received += 1 for friend in self.friends]

    # Calculations
    def reshare_prob(self, friend):  # Definition 4       p(i,j)
        return float(friend.get_number_reshares()/friend.get_num_msgs_recieved())

    def like_prob(self, friend): # Lemma 4                m(i,j)
        return float(friend.get_number_likes()/friend.get_num_msgs_recieved())

    def get_max_like_prob(self):
        return max([self.like_prob(friend) for friend in self.friends])

    def entropy_protecting_msg_from_friend(self, msg, friend):   # Lemma 2    H(X|Y)
        k, k1, t, p = float(msg.k), float(msg.k-1), float(friend.trust), float(self.reshare_prob(friend))
        a = (k-k1*t*(1-p))/k
        b = a * math.log2(1/a)
        c = (k1*t*(1-p))/k
        d = c * math.log2(k/(t*(1-p)))
        return b + d

    def information_leakage(self, msg, friend):     # Proposition 2      f(i,j) of S
        return 1 - self.entropy_protecting_msg_from_friend(msg, friend)/msg.calc_entropy()

    def risk_sharing_with_friend(self, msg, friend):    # Definition 3  r(i,j) of S
        return -self.information_leakage(msg, friend) * msg.sensitivity

    def social_benefit(self, msg, friend):      # Proposition 3      b(i,j) of S
        return self.seen_like + (1-self.seen_like) * (self.like_prob(friend)/self.get_max_like_prob())

    def utility_sharing_msg_with_friend(self, msg, friend):    # Definition 1    u(i,j) of S
        return (1-self.benefit_risk) * self.social_benefit(msg, friend) + \
               self.benefit_risk*self.risk_sharing_with_friend(msg, friend)


class Friend(Person):
    def __init__(self, name, trust):
        self.trust = trust
        self.num_reshares = 0
        self.num_likes = 0
        self.num_received = 0
        super(Friend, self).__init__(name)

    def __str__(self):
        return "Friend. {}, Trust: {}, Num Reshares: {}, Num Likes: {}, Num Recieved: {}".format(self.name, self.trust, self.num_reshares, self.num_likes, self.num_received)

    def get_num_msgs_recieved(self):
        return self.num_received

    def get_number_reshares(self):
        return self.num_reshares

    def get_number_likes(self):
        return self.num_likes


class Message:
    def __init__(self, uID, k, sensitivity):
        self.id = uID
        self.k = k
        self.sensitivity = sensitivity

    def __str__(self):
        return "Msg.{} k: {} Snesitivity: {}".format(self.id, self.k, self.sensitivity)

    def calc_entropy(self): # Lemma 1     H(X)
        return math.log(self.k, 2)


def get_inputs():
    with open("./data/config.txt", "r") as conf:
        people = conf.readlines()

    with open("./data/log.txt", "r") as logf:
        log_commands = logf.readlines()

    return people, log_commands


def iterate_log(log):
    for i in log:
        yield i


def create_people(config):
    def parse_line(ln):
        # Get str name and parse other numbers into floats
        # Returns array of elements on the input line
        lines = str(ln).replace("\n", "").split(" ")
        for i in range(1, len(lines)):
            lines[i] = float(lines[i])
        return lines

    # Create the User
    conf = parse_line(config[0])
    user = User(name=conf[0], benefit_risk=conf[1], seen_like=conf[2])

    # Create the friends and add to array
    friends = []
    for line in range(1, len(config)):
        conf = parse_line(config[line])
        friends.append(Friend(name=conf[0], trust=conf[1]))
    return user, friends


def create_steps(log, user, friends):
    messages = []

    def get_friend_with_name(name):
        for i in friends:
            if i.name == name:
                return i

    def get_msg(uID):
        for i in messages:
            if i.id == uID:
                return i

    # Parses all the steps in log into correct format
    log = [str(ln).replace("\n", "").split(" ") for ln in log]

    # Creates messages instances for all posts
    for ln in log:
        if len(ln) == 4:
            messages.append(Message(int(ln[1]), int(ln[2]), float(ln[3])))

    # Creates each step with the (Type, Person, Msg)
    # unless its activate in which case it is just (Type)
    steps = []
    for ln in log:
        if len(ln) == 4:
            steps.append([Func.Post, user, get_msg(int(ln[1]))])

        elif ln.count("like") > 0:
            steps.append([Func.Like, get_friend_with_name(ln[0]), get_msg(int(ln[1]))])

        elif ln.count("share") > 0:
            steps.append([Func.Share, get_friend_with_name(ln[0]), get_msg(int(ln[1]))])

        elif ln.count("activate") > 0:
            steps.append([Func.Activate])

        else:
            raise Exception("Step not parsable:  {}".format(ln))

    return messages, steps


def main():
    # Get the inputs into text arrays
    config, log = get_inputs()
    # Create the generator to wield each line of log
    user, friends = create_people(config)
    messages, steps = create_steps(log, user, friends)
    user.set_messages(messages)
    user.set_friends(friends)

    log_gen = iterate_log(steps)



    print("\nThe user:\n{}\n".format(user))
    print("Friends:")
    [print(friend) for friend in friends]
    
    is_activated = False
    for i in range(len(log)):
        step = next(log_gen)
        
        if step[0] == Func.Activate:
            is_activated = True
        if step[0] == Func.Post:
            step[1].increase_seen_for_friends()
        if step[0] == Func.Like:
            step[1].num_likes += 1
        if step[0] == Func.Share:
            step[1].num_reshares += 1
            
        if is_activated:
            print("Now activated")
            if step[0] == Func.Post:
                print("Utility with Friend 1: {}".format(step[1].utility_sharing_msg_with_friend(step[2], step[1].friends[0])))
                print("Utility with Friend 2: {}".format(step[1].utility_sharing_msg_with_friend(step[2], step[1].friends[1])))
                print("Utility with Friend 3: {}".format(step[1].utility_sharing_msg_with_friend(step[2], step[1].friends[2])))
                print("Utility with Friend 4: {}".format(step[1].utility_sharing_msg_with_friend(step[2], step[1].friends[3])))
                
            
            
    [print(friend) for friend in friends]
        


if __name__ == "__main__":
    main()
