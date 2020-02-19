#############################
# Code based off of idea from this paper:
# http://oro.open.ac.uk/40549/1/yang14trustcom.pdf
#
# The 'lemma' and 'definition' ids mentioned
# throughout the code are described in this paper
#############################

import os
import math
from util import print_step, Func


class User:
    """
    Class User represents the main person who is sharing posts
    -----------------
    name: name of the person
    benefit_risk: ratio of the benefit to risk of posting to a person
    seen_like: ratio of seen posts to liked posts
    messages: array of all messages posted during the log
    friends: array of all the friends created from the log
    """
    def __init__(self, name, benefit_risk, seen_like):
        self.name = name
        self.benefit_risk = benefit_risk
        self.seen_like = seen_like
        self.messages = []
        self.friends = []

    def __str__(self):
        return "User. {}, BvR: {}, SvL: {}".format(
            self.name, self.benefit_risk, self.seen_like)

    # Helper Functions
    def increase_seen_for_friends(self):
        for friend in self.friends:
            friend.num_received += 1

    # Calculations
    def reshare_prob(self, friend):  # Definition 4       p(i,j)
        return float(friend.num_reshares / friend.num_received)

    def like_prob(self, friend):  # Lemma 4                m(i,j)
        return float(friend.num_likes / friend.num_received)

    def get_max_like_prob(self):
        return max([self.like_prob(friend) for friend in self.friends])

    def entropy_protecting_msg_from_friend(self, msg, friend):  # Lemma 2    H(X|Y)
        k, k1, t, p = (float(msg.k), float(msg.k - 1), float(friend.trust), float(self.reshare_prob(friend)))
        a = (k - k1 * t * (1 - p)) / k
        b = a * math.log2(1 / a)
        c = (k1 * t * (1 - p)) / k
        d = c * math.log2(k / (t * (1 - p)))
        return b + d

    def information_leakage(self, msg, friend):  # Proposition 2      f(i,j) of S
        if msg.k == 1:
            return 0
        return (1 - self.entropy_protecting_msg_from_friend(msg, friend) / msg.calc_entropy())

    def risk_sharing_with_friend(self, msg, friend):  # Definition 3  r(i,j) of S
        return -self.information_leakage(msg, friend) * msg.sensitivity

    def social_benefit(self, msg, friend):  # Proposition 3      b(i,j) of S
        return self.seen_like + (1 - self.seen_like) * (
            self.like_prob(friend) / self.get_max_like_prob())

    # Definition 1    u(i,j) of S
    def utility_sharing_msg_with_friend(self, msg, friend):
        return (1 - self.benefit_risk) * self.social_benefit(
            msg, friend
        ) + self.benefit_risk * self.risk_sharing_with_friend(msg, friend)

    # Definition 1    u(i,j) of S
    def utility_sharing_msg_with_friends(self, msg):
        """
        [0] Returns a raw_data dictionary including all the utilities
        [1] Returns a final string with Message id and people to share it with
            e.g.:   504 Bob Cathy
        """
        raw_data = {}
        final_str = "{} ".format(msg.id)
        for friend in self.friends:
            res = self.utility_sharing_msg_with_friend(msg, friend)
            raw_data[friend.name] = res
            if res > 0:
                final_str += "{} ".format(friend.name)
        return raw_data, final_str
            

class Friend:
    """
    Class Message
    ------
    name: name of the friend
    trust: How much the user trusts this friend (changes)
    num_reshares: Number of reshares this friend does on posts from the user
    num_likes: Number of likes this friend does on posts from the user
    num_received: Number of posts this friend gets from the user
    """
    def __init__(self, name, trust):
        self.name = name
        self.trust = trust
        self.num_reshares = 0
        self.num_likes = 0
        self.num_received = 0

    def __str__(self):
        return "Friend. {}, Trust: {}, Num Reshares: {}, Num Likes: {}, Num Recieved: {}".format(
            self.name, self.trust, self.num_reshares, self.num_likes, self.num_received)


class Message:
    """
    Class Message
    ------
    id: unique id of the message
    k: Number of 'info' elements in the post
    sensitivity: How sensitive it is to the user
    """
    def __init__(self, uID, k, sensitivity):
        self.id = uID
        self.k = k
        self.sensitivity = sensitivity

    def __str__(self):
        return "Msg.{} k: {} Snesitivity: {}".format(self.id, self.k, self.sensitivity)

    def calc_entropy(self):  # Lemma 1  H(X)
        return math.log2(self.k)


def get_inputs():
    """
    Reads in the config table and the log files
    returns the list of steps
    """
    with open("./data/config.txt", "r") as conf:
        people = conf.readlines()

    with open("./data/log.txt", "r") as logf:
        log_commands = logf.readlines()

    return people, log_commands


def iterate_log(log):
    """
    Creates a function to generate the next 
    step when calling the 'next' keyword
    """
    for i in log:
        yield i


def create_people(config):
    """
    Creates the list of friends from the config file
    and the main user and sets up instances
    return the user and an array of friends
    """
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
    """
    Creates a parsed list of steps and returns them
    This has the general format of
    [function_type, friend/user, message]
    Also returns the list of messages
    """
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
    # Creates all the people from the config file
    user, friends = create_people(config)
    # Gets all the messages and parsed steps
    messages, steps = create_steps(log, user, friends)
    # Sets the messages and friends to the variables 
    # in the user instance
    user.messages = messages
    user.friends = friends
    # Creates the log generator in order to use 'next'
    log_gen = iterate_log(steps)

    # Initial logging
    print("\nThe user:\n{}\n".format(user))
    print("Friends:")
    [print(friend) for friend in friends]

    # Iterates through the parsed log steps
    is_activated = False
    for i in range(len(log)):
        step = next(log_gen)

        # Updates the relevant variables for each post type
        if step[0] == Func.Activate:
            is_activated = True
            print("--------\nNow activated\n--------")
        if step[0] == Func.Post:
            step[1].increase_seen_for_friends()
        if step[0] == Func.Like:
            step[1].num_likes += 1
        if step[0] == Func.Share:
            step[1].num_reshares += 1

        # Once activated, returns the string
        # with message id and the people to share it with
        if is_activated:
            if step[0] == Func.Post:
                print(step[1].utility_sharing_msg_with_friends(step[2])[1])


if __name__ == "__main__":
    main()
